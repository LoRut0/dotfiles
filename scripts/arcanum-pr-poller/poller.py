#!/usr/bin/env python3
"""Arcanum change detector. Only a changed snapshot can reach `codex queue`."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import random
from datetime import datetime
from email.utils import parsedate_to_datetime
import signal
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEFAULT_ROOT = Path.home() / '.local/share/arcanum-pr-poller'
API = 'https://arcanum.yandex.net/api'
SKILL_MODES = {
    'arcanum-pr-agent-helper': 'PR agent helper',
    'arcanum-auto-review': 'Auto review',
}
CHECK_KEYS = ('system', 'type', 'required', 'status', 'description', 'system_check_id',
              'system_check_uri', 'restartable', 'run_id', 'attempt')
STOP_REASONS = {
    'author_ship': 'ship автора',
    'merged': 'PR влит',
    'closed': 'PR закрыт',
    'user_request': 'по команде пользователя',
    'unknown': 'причина не сохранена',
}


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def sorted_rows(rows):
    return sorted(rows, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))


def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def normalized_comments(rows):
    result = []
    for row in rows:
        if row.get('is_draft') or row.get('draft'):
            continue
        if not isinstance(row.get('content'), str) or 'id' not in row:
            raise ValueError('Incomplete comment payload')
        # v1 returns both roots and replies as a flat list. thread_updated_at
        # additionally detects thread mutations even when root text stays intact.
        result.append({'id': str(row['id']), 'text': content_hash(row['content']),
                       'status': row.get('issue_status'),
                       'thread_updated_at': row.get('thread_updated_at'),
                       'user': row.get('user', row.get('author')),
                       'parent_id': row.get('parent_id'),
                       'reactions': row.get('reactions', [])})
    return sorted_rows(result)


def normalized_checks(rows):
    result = []
    for row in rows:
        if not all(k in row for k in ('system', 'type', 'status')):
            raise ValueError('Incomplete check payload')
        result.append({k: row.get(k) for k in CHECK_KEYS})
    return sorted_rows(result)


def canonical(metadata, active, comments, checks):
    if not all(k in metadata for k in ('id', 'status', 'description', 'summary', 'author', 'vcs', 'approvers')):
        raise ValueError('Incomplete PR metadata')
    if not all(active.get('commit_ids', {}).get(k) for k in ('head', 'base', 'merge')):
        raise ValueError('Incomplete revision payload')
    return {'metadata': {k: (sorted_rows(metadata[k]) if k == 'approvers' else metadata[k])
                         for k in ('id', 'status', 'description', 'summary', 'author', 'vcs', 'approvers')},
            'revision': active, 'comments': normalized_comments(comments),
            'checks': normalized_checks(checks)}


class Deferred(RuntimeError):
    def __init__(self, retry_at, reason):
        super().__init__(reason)
        self.retry_at = retry_at
        self.reason = reason


class HTTPFailure(RuntimeError):
    def __init__(self, status, retry_after=None):
        super().__init__('Arcanum HTTP ' + str(status))
        self.status = status
        self.retry_after = retry_after


def retry_after_seconds(value, now):
    if not value:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        try:
            return max(0, parsedate_to_datetime(value).timestamp() - now)
        except (TypeError, ValueError, OverflowError):
            return 0


class RequestGovernor:
    """Shared process-safe request spacing, rolling budget and server cooldown."""
    def __init__(self, root, minimum_gap=2, hourly_limit=120, clock=time.time, sleep=time.sleep):
        self.root = Path(root)
        self.minimum_gap = max(0, minimum_gap)
        self.hourly_limit = max(1, hourly_limit)
        self.clock, self.sleep = clock, sleep

    @contextlib.contextmanager
    def state(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.root / 'http.lock', 'a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            path = self.root / 'http-budget.json'
            data = read_json(path, {'requests': []})
            try:
                yield data
            finally:
                atomic_json(path, data)
                fcntl.flock(stream, fcntl.LOCK_UN)

    def before_request(self):
        with self.state() as data:
            now = self.clock()
            if data.get('blocked_until', 0) > now:
                raise Deferred(data['blocked_until'], 'server-cooldown')
            requests = [stamp for stamp in data['requests'] if stamp > now - 3600]
            if len(requests) >= self.hourly_limit:
                raise Deferred(requests[0] + 3600, 'hourly-budget')
            delay = max(0, data.get('last_request_at', 0) + self.minimum_gap - now)
            if delay:
                self.sleep(delay)
            now = self.clock()
            data['requests'] = requests + [now]
            data['last_request_at'] = now

    def failed(self, error):
        if error.status not in (401, 403, 429, 503):
            return
        with self.state() as data:
            failures = data.get('server_failures', 0) + 1
            delay = 3600 if error.status in (401, 403) else min(3600, 60 * 2 ** min(failures - 1, 6))
            delay = max(delay, retry_after_seconds(error.retry_after, self.clock()))
            data.update(server_failures=failures,
                        blocked_until=max(data.get('blocked_until', 0), self.clock() + delay),
                        last_http_status=error.status)

    def succeeded(self):
        with self.state() as data:
            data['server_failures'] = 0


def stable_tree(value):
    if isinstance(value, dict):
        return {key: stable_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return sorted_rows([stable_tree(item) for item in value])
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unexpected API redirect')


class Arcanum:
    def __init__(self, config):
        # The existing SkillStore chain supplies short-lived credentials. No
        # browser stores, token files of our own, or tokens in argv/logs/config.
        sys.path.insert(0, str(Path(config['arcanum_skill']) / 'scripts'))
        import arcanum_tool
        def expired(signum, frame):
            raise TimeoutError('Arcanum authentication timed out')
        old = signal.signal(signal.SIGALRM, expired)
        signal.alarm(45)
        try:
            self.token = arcanum_tool.get_token('arcanum', allow_interactive=False)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
        if not self.token:
            raise ValueError('Arcanum authentication unavailable; use standard store setup')
        ca = config.get('ca_bundle')
        if not ca or not Path(ca).is_file():
            raise ValueError('Configured Yandex CA bundle is unavailable')
        self.request_count = 0
        self.max_requests = config.get('max_requests_per_pass', 16)
        self.governor = RequestGovernor(config.get('_runtime_root', DEFAULT_ROOT),
            config.get('minimum_request_gap_seconds', 2), config.get('max_requests_per_hour', 120))
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(
            context=ssl.create_default_context(cafile=ca)))

    def page(self, url):
        # Pagination is untrusted input; never forward OAuth to another origin.
        if not url.startswith(API + '/'):
            raise ValueError('Unsafe API/pagination URL')
        if self.request_count >= self.max_requests:
            raise Deferred(time.time() + 900, 'per-pass-budget')
        self.governor.before_request()
        self.request_count += 1
        request = urllib.request.Request(url, headers={'Authorization': 'OAuth ' + self.token,
                                                      'Accept': 'application/json'})
        try:
            with self.opener.open(request, timeout=25) as response:
                payload = json.load(response)
                headers = dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            error = HTTPFailure(exc.code, exc.headers.get('Retry-After'))
            self.governor.failed(error)
            raise error from None
        if not isinstance(payload, dict) or 'data' not in payload or payload.get('errors'):
            raise ValueError('Invalid Arcanum envelope')
        self.governor.succeeded()
        return payload, {k.lower(): v for k, v in headers.items()}

    def get(self, path, collection=False):
        url, seen, result = API + path, set(), []
        total = None
        for _ in range(100):
            if url in seen:
                raise ValueError('Pagination loop')
            seen.add(url)
            obj, headers = self.page(url)
            data = obj['data']
            if not collection:
                if not isinstance(data, dict):
                    raise ValueError('Expected API object')
                return data
            if not isinstance(data, list):
                raise ValueError('Expected API list')
            result.extend(data)
            link = re.search(r'<([^>]+)>;\s*rel="?next"?', headers.get('link', ''))
            paging = obj.get('pagination', {}) or {}
            next_url = (link.group(1) if link else None) or paging.get('next') or obj.get('next')
            count = headers.get('x-total-count', paging.get('total', obj.get('total')))
            if count is not None:
                total = int(count)
            if next_url:
                if not isinstance(next_url, str) or not (next_url.startswith('/') or next_url.startswith('https://')):
                    raise ValueError('Unsupported pagination cursor')
                url = urllib.parse.urljoin(url, next_url)
                continue
            if (headers.get('x-next-page') or headers.get('x-next-cursor') or
                    paging.get('has_more') or obj.get('has_more') or paging.get('next_cursor')):
                raise ValueError('Unsupported pagination: refusing partial snapshot')
            if total is not None and len(result) != total:
                raise ValueError('Incomplete paginated list')
            return result
        raise ValueError('Too many API pages')

    def probe(self, pr):
        # Swagger-backed field projection. PR.updated_at is NOT a universal
        # clock: real checks in our sample were newer than PR.updated_at.
        metadata = self.get(f'/v1/review-requests/{pr}?fields=id,updated_at,state,full_status,'
            'active_diff_set(id,patch_vcs_ids(arc_branch_heads(from_id,to_id,merge_id))),'
            'checks(system,type,status,required,updated_at,system_check_id),approvers(uid,name)')
        comments = self.get(f'/v2/public/pull-request/{pr}/comment?fields=id,reply_to_id,'
            'is_draft,updated_at,thread_updated_at,issue_status,deleted_at,reactions(id,code,updated_at)',
            collection=True)
        if not all(key in metadata for key in ('id', 'updated_at', 'state', 'full_status',
                                               'active_diff_set', 'checks', 'approvers')):
            raise ValueError('Incomplete compact PR metadata')
        active = metadata['active_diff_set']
        heads = active.get('patch_vcs_ids', {}).get('arc_branch_heads', {})
        if not active.get('id') or not all(heads.get(k) for k in ('from_id', 'to_id', 'merge_id')):
            raise ValueError('Incomplete compact revision')
        for check in metadata['checks']:
            if not all(k in check for k in ('system', 'type', 'status', 'updated_at')):
                raise ValueError('Incomplete compact check')
        published = []
        for comment in comments:
            if not all(k in comment for k in ('id', 'is_draft', 'updated_at', 'thread_updated_at')):
                raise ValueError('Incomplete compact comment')
            if not comment['is_draft']:
                published.append(comment)
        return stable_tree({'version': 1, 'pr': metadata, 'comments': published})

    def fetch(self, pr):
        metadata_path = (f'/v2/pull-requests/{pr}?fields=id,url,author(id,login,name),'
                         'summary,description,status,vcs(from_branch,to_branch),approvers(id,login,name)')
        active_path = f'/v1/pull-requests/{pr}/active-diff?fields=id,commit_ids(base,merge,head)'
        metadata = self.get(metadata_path)
        active = self.get(active_path)
        comments = self.get(f'/v1/review-requests/{pr}/comments', collection=True)
        checks = self.get(f'/v1/review-requests/{pr}/diff-sets/{active["id"]}/checks', collection=True)
        if active != self.get(active_path) or metadata != self.get(metadata_path):
            raise ValueError('PR changed while fetching; retry next poll')
        return canonical(metadata, active, comments, checks)


@contextlib.contextmanager
def lock(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def changed_sections(before, after):
    return [key for key in after if before.get(key) != after[key]]


def legacy_comparison(snapshot, legacy):
    """Compare migrated agent observations without treating new schema as a change."""
    observed = legacy.get('observed', {})
    revision = legacy.get('reviewed_active_diff', {}).get('commit_ids') or observed
    if not revision:
        raise ValueError('Cannot establish legacy revision; explicit baseline required')
    changes = []
    for key in ('head', 'base', 'merge'):
        if revision.get(key) != snapshot['revision']['commit_ids'][key]:
            changes.append('revision')
            break
    old_comments = legacy.get('comments')
    if not isinstance(old_comments, list):
        raise ValueError('Cannot establish legacy comments')
    def compact_new(row):
        return (row['id'], row['text'], row['status'])
    old = sorted((str(c['id']), c.get('text_sha256', c.get('content_sha256')),
                  c.get('issue_status', c.get('status'))) for c in old_comments
                 if not c.get('is_draft'))
    if old != sorted(compact_new(c) for c in snapshot['comments']):
        changes.append('comments')
    checks = legacy.get('checks', legacy.get('ci'))
    if isinstance(checks, dict):
        checks = checks.get('items')
    if not isinstance(checks, list):
        raise ValueError('Cannot establish legacy CI')
    normalized_checks(checks)  # Validate the legacy structure before masking fields.
    common = set(CHECK_KEYS).intersection(*(set(row) for row in checks)) if checks else set(CHECK_KEYS)
    masked = lambda rows: sorted_rows([{k: row.get(k) for k in common} for row in rows])
    if masked(checks) != masked(snapshot['checks']):
        changes.append('checks')
    description_hash = observed.get('pr_description_sha256', legacy.get('description_sha256'))
    if description_hash and description_hash != content_hash(snapshot['metadata']['description']):
        changes.append('description')
    old_status = observed.get('pr_status', 'open')
    if snapshot['metadata']['status'] != old_status:
        changes.append('status')
    # Newly required author-ship handling is an actionable observed PR state.
    if snapshot['metadata']['author'] in snapshot['metadata']['approvers']:
        changes.append('author_approval')
    return list(dict.fromkeys(changes))


def prompt_for(config, event, root):
    event_path = root / config['pr_id'] / 'events' / (event['id'] + '.json')
    script = root / 'poller.py'
    return (f"Скрипт обнаружил изменение Arcanum PR {config['pr_id']}: "
            f"{', '.join(event['changes'])}. Это один событийный проход, не запуск расписания. "
            f"Прочитай скилл {config['skill_path']} и выполни один проход ревью/сопровождения. "
            f"Состояние ревью: {config['review_state']}. Снимок события: {event_path}. "
            "Все исходящие issues, комментарии и ответы создавай "
            "только как drafts (draft=true); публикация и смена статусов issues требуют "
            "явного подтверждения пользователя конкретного набора. Прежнее разрешение "
            "автоматической публикации из истории чата/state больше не действует. "
            "Следуй references/draft-publication.md выбранного скилла. "
            "Сохрани остальные ограничения и полномочия текущего чата. "
            "Вначале проверь условия остановки и актуальное состояние PR. "
            "После подготовки drafts сохрани awaiting_approval в state и заверши проход: "
            "ожидание согласия не должно удерживать inflight или создавать повторные вызовы модели. "
            "После прохода сохрани state ревью, затем обязательно подтверди обработку командой "
            f"{sys.executable} {script} --root {root} ack --pr {config['pr_id']} "
            f"--event {event['id']}. Если мониторинг надо закончить, добавь --stop "
            "и --reason author_ship, merged, closed или user_request по фактической причине. "
            "При невозможности закончить проход добавь --outcome blocked: повторного "
            "запуска на том же состоянии не будет, незавершённая работа остаётся в state. "
            "Не меняй снимок события. Не обновляй baseline свежим снимком за пределами "
            "обработанного события: новые изменения должны остаться для следующего прохода.")


def queue_event(config, event, root):
    return subprocess.run([config['codex'], 'queue', '--thread', config['thread_id'],
                           '--message', prompt_for(config, event, root)],
                          capture_output=True, text=True, timeout=60,
                          stdin=subprocess.DEVNULL)


def process(config, root, fetch, send=queue_event, now=None, force=False, dry_run=False, probe=None):
    now = time.time() if now is None else now
    directory = root / config['pr_id']
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock(directory / 'poll.lock') as acquired:
        if not acquired:
            return 'locked'
        path = directory / 'poll-state.json'
        state = read_json(path, {'version': 1})
        if state.get('stopped') or not config.get('enabled', True):
            return 'stopped'
        if now < state.get('retry_not_before', 0):
            return 'backoff'
        if not force and now < state.get('next_poll_at', 0):
            return 'not-due'
        if state.get('inflight'):
            return 'awaiting-ack'  # No remote reads while the agent owns this event.
        jitter = random.uniform(0, config.get('jitter_seconds', 0))
        compact = None
        try:
            if probe is not None:
                compact = probe(config['pr_id'])
                signature = digest(compact)
                reconcile = now - state.get('last_full_fetch_at', 0) >= config.get('reconcile_seconds', 21600)
                if (state.get('probe_signature') == signature and 'baseline' in state and not reconcile):
                    state.update(last_checked_at=now, next_poll_at=now + config['interval_seconds'] + jitter,
                                 consecutive_errors=0, last_poll_kind='compact')
                    state.pop('last_error', None)
                    if not dry_run:
                        atomic_json(path, state)
                    return 'unchanged-light'
            snapshot = fetch(config['pr_id'])
        except Exception as exc:
            # Error type only: exceptions from external auth/network may contain
            # sensitive output. Never turn network/auth errors into model calls.
            failures = state.get('consecutive_errors', 0) + 1
            delay = min(3600, config['interval_seconds'] * 2 ** min(failures - 1, 6))
            if isinstance(exc, HTTPFailure):
                delay = max(delay, retry_after_seconds(exc.retry_after, now))
                state['last_http_status'] = exc.status
                if exc.status in (401, 403):
                    delay = max(delay, 3600)
            if isinstance(exc, Deferred):
                delay = max(delay, exc.retry_at - now)
            state.update(next_poll_at=now + delay + jitter, retry_not_before=now + delay,
                         last_error=type(exc).__name__, last_error_at=now, consecutive_errors=failures)
            if not dry_run:
                atomic_json(path, state)
            return 'fetch-error:' + type(exc).__name__
        state.update(last_checked_at=now, next_poll_at=now + config['interval_seconds'] + jitter,
                     consecutive_errors=0, last_full_fetch_at=now, last_poll_kind='full')
        state['title'] = snapshot['metadata']['summary']
        state['author'] = snapshot['metadata']['author']
        if compact is not None:
            state['probe_signature'] = digest(compact)
        state.pop('last_error', None)
        atomic_json(directory / 'latest-snapshot.json', snapshot)
        if 'baseline' not in state:
            try:
                legacy = read_json(config['review_state'])
                changes = legacy_comparison(snapshot, legacy)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                state['last_error'] = 'legacy-state:' + type(exc).__name__
                if not dry_run:
                    atomic_json(path, state)
                return 'migration-error'
            if not changes:
                if not dry_run:
                    state['baseline'] = snapshot
                    state['baseline_source'] = 'verified-legacy-observation'
                    atomic_json(path, state)
                return 'baseline-unchanged'
        else:
            changes = changed_sections(state['baseline'], snapshot)
        if state.get('inflight'):
            if not dry_run:
                atomic_json(path, state)
            return 'awaiting-ack'
        if not changes:
            if not dry_run:
                atomic_json(path, state)
            return 'unchanged'
        if dry_run:
            return 'would-queue:' + ','.join(changes)
        event = {'id': str(uuid.uuid4()), 'pr_id': config['pr_id'], 'created_at': now,
                 'changes': changes, 'snapshot': snapshot, 'snapshot_sha256': digest(snapshot)}
        atomic_json(directory / 'events' / (event['id'] + '.json'), event)
        state['inflight'] = {'event_id': event['id'], 'status': 'sending', 'since': now}
        atomic_json(path, state)  # Persist before the external side effect.
        try:
            result = send(config, event, root)
            state['inflight']['status'] = 'queued' if result.returncode == 0 else 'uncertain'
            state['inflight']['exit_code'] = result.returncode
        except (subprocess.TimeoutExpired, OSError):
            state['inflight']['status'] = 'uncertain'
        # No automatic resubmission: queue acceptance may have preceded a crash.
        atomic_json(path, state)
        return state['inflight']['status']


def acknowledge(root, pr, event_id, outcome='complete', stop=False, reason=None):
    if reason is not None and (not stop or reason not in STOP_REASONS):
        raise ValueError('A valid stop reason requires --stop')
    directory = root / pr
    with lock(directory / 'poll.lock') as acquired:
        if not acquired:
            raise ValueError('Poll in progress; retry ack shortly')
        path = directory / 'poll-state.json'
        state = read_json(path)
        if state.get('last_ack', {}).get('event_id') == event_id:
            return 'already-acked'
        if state.get('inflight', {}).get('event_id') != event_id:
            raise ValueError('Event is not the active delivery')
        event = read_json(directory / 'events' / (event_id + '.json'))
        if event['pr_id'] != pr or digest(event['snapshot']) != event['snapshot_sha256']:
            raise ValueError('Event integrity mismatch')
        state['baseline'] = event['snapshot']
        state['title'] = event['snapshot']['metadata']['summary']
        state['author'] = event['snapshot']['metadata']['author']
        state['last_ack'] = {'event_id': event_id, 'at': time.time(), 'outcome': outcome}
        state.pop('inflight')
        if stop:
            state['stopped'] = True
            state['stop_reason'] = reason or 'unknown'
            state['stopped_at'] = time.time()
        atomic_json(path, state)
        return 'acked'


def saved_title(state):
    """Older states already contain the title inside their full baseline."""
    return state.get('title', state.get('baseline', {}).get('metadata', {}).get('summary'))


def saved_author(state):
    return state.get('author') or state.get('baseline', {}).get('metadata', {}).get('author')


def load_status_state(root, monitor):
    """Read local identity and legacy stop evidence without guessing from PR state."""
    state = read_json(root / monitor['pr_id'] / 'poll-state.json', {})
    state['author'] = saved_author(state)
    if state.get('stopped') and state.get('stop_reason') is None:
        state['stop_reason'] = 'unknown'
        path = monitor.get('review_state')
        try:
            review = read_json(path, {}) if path else {}
        except (OSError, ValueError):
            review = {}
        terminal = review.get('terminal', {}) if isinstance(review, dict) else {}
        if isinstance(terminal, dict):
            reason = terminal.get('reason')
            stop_event = terminal.get('event_id')
            ack_event = state.get('last_ack', {}).get('event_id')
            # A record from a previous run must not explain a later stop.
            matching_event = stop_event is not None and stop_event == ack_event
            if matching_event and reason in STOP_REASONS:
                state['stop_reason'] = reason
    return state


def single_line(value):
    return ' '.join(''.join(char for char in str(value)
                            if char.isprintable() or char.isspace()).split())


def author_label(author):
    if isinstance(author, dict):
        author = author.get('login') or author.get('name') or author.get('uid') or author.get('id')
    return single_line(author) if author is not None else '—'


def monitor_skill(monitor):
    path = monitor.get('skill_path')
    return Path(path).parent.name if path else None


def monitor_mode(monitor):
    skill = monitor_skill(monitor)
    return SKILL_MODES.get(skill, skill)


def human_status(monitors, states, now=None, blocked_until=0):
    """Format saved monitor state; do not contact Arcanum or launch an agent."""
    now = time.time() if now is None else now
    zone = datetime.fromtimestamp(now).astimezone().strftime('%Z (%z)')
    if not monitors:
        return 'Нет зарегистрированных PR.'

    def timestamp(value):
        return '—' if value is None else datetime.fromtimestamp(value).astimezone().strftime('%d.%m %H:%M:%S')

    rows = [('PR', 'Автор', 'Режим', 'Состояние', 'Интервал', 'Последний опрос', 'Следующий опрос', 'Название')]
    notes = []
    for monitor, state in zip(monitors, states):
        pr = monitor['pr_id']
        inflight = state.get('inflight')
        next_at = max(state.get('next_poll_at', 0), state.get('retry_not_before', 0), blocked_until)
        next_label = timestamp(next_at) if next_at > now else 'при следующем тике'
        if state.get('stopped') or not monitor.get('enabled', True):
            reason = STOP_REASONS.get(state.get('stop_reason'), STOP_REASONS['unknown'])
            if not state.get('stopped'):
                reason = 'отключён в конфигурации'
            status, next_label = f'Остановлен ({reason})', '—'
        elif inflight:
            status = ('Ждёт завершения ревью' if inflight.get('status') == 'queued'
                      else 'Доставка не подтверждена')
            next_label = 'после подтверждения'
            notes.append(f"PR {pr}: событие {inflight.get('event_id', '—')}")
        elif max(state.get('retry_not_before', 0), blocked_until) > now:
            status = 'Пауза перед повтором'
        elif state.get('last_error'):
            status = 'Ошибка опроса'
        elif state.get('last_checked_at') is None:
            status = 'Ожидает первого опроса'
        else:
            status = 'Ожидает опроса'
        interval = monitor['interval_seconds']
        interval_label = f'{interval // 60} мин' if interval % 60 == 0 else f'{interval} с'
        # PR titles are remote text: keep terminal escapes and line breaks out
        # of the table while retaining the original title in state/JSON.
        title = saved_title(state) or '—'
        title = single_line(title)
        rows.append((pr, author_label(saved_author(state)), single_line(monitor_mode(monitor) or '—'),
                     status, interval_label,
                     timestamp(state.get('last_checked_at')), next_label, title))
        if state.get('last_error'):
            error = state['last_error']
            code = state.get('last_http_status')
            if error == 'HTTPFailure' and code is not None:
                error += f' (HTTP {code})'
            notes.append(f'PR {pr}: последняя ошибка — {error}')

    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    lines = [f'Сохранённое состояние мониторов. Время: {zone}.', '']
    for row in rows:
        lines.append('  '.join(value.ljust(width) for value, width in zip(row, widths)).rstrip())
    if notes:
        lines.extend(['', *notes])
    return '\n'.join(lines)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('tick', 'check'):
        p = sub.add_parser(name)
        p.add_argument('--pr')
        p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('ack')
    p.add_argument('--pr', required=True)
    p.add_argument('--event', required=True)
    p.add_argument('--outcome', choices=['complete', 'blocked'], default='complete')
    p.add_argument('--stop', action='store_true')
    p.add_argument('--reason', choices=STOP_REASONS, help='Reason for stopping (requires --stop)')
    for name in ('stop', 'resume'):
        p = sub.add_parser(name)
        p.add_argument('--pr', required=True)
        if name == 'stop':
            p.add_argument('--reason', choices=STOP_REASONS, default='user_request',
                           help='Stop reason (default: user_request)')
    p = sub.add_parser('register')
    p.add_argument('--pr', required=True)
    p.add_argument('--thread', required=True)
    p.add_argument('--skill', required=True)
    p.add_argument('--review-state', required=True)
    p.add_argument('--interval', required=True, type=int, choices=[600, 900])
    p.add_argument('--codex', default='/opt/homebrew/bin/codex')
    p = sub.add_parser('status')
    p.add_argument('--human', action='store_true',
                   help='Show a readable table with local times instead of JSON')
    args = parser.parse_args()
    if args.command == 'ack' and args.reason is not None and not args.stop:
        parser.error('--reason requires --stop for ack')
    config = read_json(args.root / 'config.json')
    config['_runtime_root'] = str(args.root)
    if args.command == 'register':
        if not re.fullmatch(r'\d{8}', args.pr):
            raise ValueError('Expected eight-digit PR ID')
        uuid.UUID(args.thread)
        if any(m['pr_id'] == args.pr for m in config['monitors']):
            raise ValueError('PR already registered; inspect status before changing owner')
        for value in (args.skill, args.review_state, args.codex):
            if not Path(value).is_absolute() or not Path(value).is_file():
                raise ValueError('Expected existing absolute file path')
        with lock(args.root / 'config.lock') as ok:
            if not ok:
                raise ValueError('Config busy')
            config = read_json(args.root / 'config.json')
            if any(m['pr_id'] == args.pr for m in config['monitors']):
                raise ValueError('PR already registered')
            config['monitors'].append({'pr_id':args.pr, 'thread_id':args.thread,
                'skill_path':args.skill, 'review_state':args.review_state,
                'interval_seconds':args.interval, 'codex':args.codex, 'enabled':True})
            atomic_json(args.root / 'config.json', config)
        print('registered')
        return
    if args.command == 'ack':
        print(acknowledge(args.root, args.pr, args.event, args.outcome, args.stop, args.reason))
        return
    if args.command in ('stop', 'resume'):
        directory = args.root / args.pr
        with lock(directory / 'poll.lock') as ok:
            if not ok:
                raise ValueError('Poll in progress')
            state = read_json(directory / 'poll-state.json', {'version': 1})
            state['stopped'] = args.command == 'stop'
            if args.command == 'resume':
                state['next_poll_at'] = 0
                state.pop('stop_reason', None)
                state.pop('stopped_at', None)
            else:
                state['stop_reason'] = args.reason
                state['stopped_at'] = time.time()
            atomic_json(directory / 'poll-state.json', state)
        return
    if args.command == 'status' and args.human:
        states = [load_status_state(args.root, monitor)
                  for monitor in config['monitors']]
        budget = read_json(args.root / 'http-budget.json', {})
        print(human_status(config['monitors'], states, blocked_until=budget.get('blocked_until', 0)))
        return
    for monitor in config['monitors']:
        pr = monitor['pr_id']
        if getattr(args, 'pr', None) and args.pr != pr:
            continue
        if args.command == 'status':
            state = load_status_state(args.root, monitor)
            print(json.dumps({'pr': pr, 'interval': monitor['interval_seconds'], 'title': saved_title(state),
                              **{k:v for k,v in state.items() if k != 'baseline'},
                              'skill': monitor_skill(monitor), 'mode': monitor_mode(monitor)}, ensure_ascii=False))
            continue
        try:
            # Lazy auth: not-due/stopped jobs never authenticate or call any API.
            client = None
            def get_client():
                nonlocal client
                if client is None:
                    client = Arcanum(config)
                return client
            monitor = dict(monitor, jitter_seconds=config.get('jitter_seconds', 30),
                           reconcile_seconds=config.get('reconcile_seconds', 21600))
            outcome = process(monitor, args.root, lambda pr: get_client().fetch(pr),
                              force=args.command == 'check', dry_run=args.dry_run,
                              probe=lambda pr: get_client().probe(pr))
            if outcome not in ('not-due', 'stopped', 'awaiting-ack', 'backoff'):
                print(json.dumps({'at': time.time(), 'pr': pr, 'outcome': outcome,
                                  'http_requests': client.request_count if client else 0}), flush=True)
        except Exception as exc:
            print(json.dumps({'at': time.time(), 'pr': pr,
                              'error': type(exc).__name__}), flush=True)


if __name__ == '__main__':
    main()
