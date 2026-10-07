import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

import poller as p


def snapshot():
    return p.canonical({'id': 12345678, 'summary': 'Title', 'description': 'Requirements',
                        'status': 'open', 'author': {'name': 'author'}, 'vcs': {}, 'approvers': []},
                       {'id': 7, 'commit_ids': {'head': 'h1', 'base': 'b1', 'merge': 'm1'}},
                       [{'id': 1, 'content': 'Question', 'issue_status': 'open',
                         'thread_updated_at': 't1', 'user': {'name': 'reviewer'}}],
                       [{'system': 'ci', 'type': 'test', 'status': 'success', 'system_check_id': 'r1'}])


class PollFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {'pr_id': '12345678', 'interval_seconds': 900,
                       'review_state': str(self.root/'review.json')}
        self.sent = []
        self.original = snapshot()
        p.atomic_json(self.root/'12345678/poll-state.json', {'baseline': self.original})

    def send(self, config, event, root):
        self.sent.append(event)
        return SimpleNamespace(returncode=0)

    def run_poll(self, value, **kwargs):
        return p.process(self.config, self.root, lambda _: value, self.send, **kwargs)

    def state(self):
        return p.read_json(self.root/'12345678/poll-state.json')


class DeliveryTests(PollFixture):
    def test_title_is_saved_and_renamed_with_metadata(self):
        self.assertEqual(self.run_poll(self.original, now=0), 'unchanged')
        self.assertEqual(self.state()['title'], 'Title')
        self.assertEqual(self.state()['author'], {'name': 'author'})
        renamed = copy.deepcopy(self.original)
        renamed['metadata']['summary'] = 'Renamed PR'
        self.assertEqual(self.run_poll(renamed, now=900), 'queued')
        self.assertEqual(self.state()['title'], 'Renamed PR')
        p.acknowledge(self.root, '12345678', self.sent[-1]['id'])
        self.assertEqual(self.state()['title'], 'Renamed PR')

    def test_unchanged_never_invokes_model(self):
        for now in range(0, 3600, 900):
            self.assertEqual(self.run_poll(self.original, now=now), 'unchanged')
        self.assertEqual(self.sent, [])

    def test_timer_does_not_fetch_before_due(self):
        self.run_poll(self.original, now=100)
        def forbidden(_):
            raise AssertionError('Unexpected request')
        self.assertEqual(p.process(self.config, self.root, forbidden, now=101), 'not-due')

    def test_commit_reply_issue_ci_and_description_each_trigger(self):
        changes = [lambda s:s['revision']['commit_ids'].update(head='h2'),
                   lambda s:s['comments'][0].update(text='edited'),
                   lambda s:s['comments'].append({'id':'2','text':'reply'}),
                   lambda s:s['comments'][0].update(status='resolved'),
                   lambda s:s['checks'][0].update(system_check_id='r2'),
                   lambda s:s['metadata'].update(description='New requirements'),
                   lambda s:s['metadata'].update(status='merged'),
                   lambda s:s['metadata'].update(approvers=[{'name':'author'}])]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                p.atomic_json(self.root/'12345678/poll-state.json', {'baseline':self.original})
                value=copy.deepcopy(self.original); mutate(value)
                self.assertEqual(self.run_poll(value, now=100), 'queued')
                self.assertEqual(self.run_poll(value, now=1000), 'awaiting-ack')
        self.assertEqual(len(self.sent), len(changes))

    def test_new_changes_during_review_survive_ack(self):
        one=copy.deepcopy(self.original);one['metadata']['summary']='Changed'
        self.run_poll(one, now=0)
        event=self.sent[-1]['id']
        two=copy.deepcopy(one);two['metadata']['description']='New'
        self.assertEqual(self.run_poll(two, now=900), 'awaiting-ack')
        p.acknowledge(self.root,'12345678',event)
        self.assertEqual(self.run_poll(two, now=1800), 'queued')
        self.assertEqual(len(self.sent),2)

    def test_ack_is_idempotent_and_unchanged_stays_quiet(self):
        one=copy.deepcopy(self.original);one['checks'][0]['status']='failure'
        self.run_poll(one,now=0);event=self.sent[-1]['id']
        self.assertEqual(p.acknowledge(self.root,'12345678',event), 'acked')
        self.assertEqual(p.acknowledge(self.root,'12345678',event), 'already-acked')
        self.assertEqual(self.run_poll(one, now=900), 'unchanged')
        self.assertEqual(len(self.sent),1)

    def test_api_failure_preserves_baseline_and_never_dispatches(self):
        def fail(_): raise ValueError('secret must not be logged')
        self.assertEqual(p.process(self.config,self.root,fail,self.send,now=0), 'fetch-error:ValueError')
        self.assertEqual(self.state()['baseline'],self.original)
        self.assertNotIn('secret',json.dumps(self.state()))
        self.assertEqual(self.sent,[])

    def test_timeout_never_resubmits_blindly(self):
        one=copy.deepcopy(self.original);one['metadata']['summary']='new'
        def timeout(*args): raise subprocess.TimeoutExpired('codex',60)
        self.assertEqual(p.process(self.config,self.root,lambda _:one,timeout,now=0),'uncertain')
        self.assertEqual(self.run_poll(one,now=900),'awaiting-ack')
        self.assertEqual(self.sent,[])

    def test_stopped_never_calls_api(self):
        p.atomic_json(self.root/'12345678/poll-state.json',{'stopped':True})
        def forbidden(_): raise AssertionError()
        self.assertEqual(p.process(self.config,self.root,forbidden,self.send),'stopped')

    def test_blocked_ack_does_not_retry_without_changes(self):
        one=copy.deepcopy(self.original);one['metadata']['summary']='new'
        self.run_poll(one,now=0)
        p.acknowledge(self.root,'12345678',self.sent[-1]['id'],'blocked')
        self.assertEqual(self.run_poll(one,now=900),'unchanged')
        self.assertEqual(len(self.sent),1)

    def test_dry_run_has_no_dispatch_or_ack_state_mutation(self):
        one=copy.deepcopy(self.original);one['metadata']['summary']='new'
        self.assertEqual(self.run_poll(one,now=0,dry_run=True),'would-queue:metadata')
        self.assertEqual(self.state(),{'baseline':self.original})
        self.assertEqual(self.sent,[])

    def test_shared_lock_prevents_second_poll(self):
        with p.lock(self.root/'12345678/poll.lock'):
            self.assertEqual(self.run_poll(self.original), 'locked')
        self.assertEqual(self.sent,[])

    def test_bad_event_cannot_ack(self):
        one=copy.deepcopy(self.original);one['metadata']['summary']='new'
        self.run_poll(one,now=0)
        with self.assertRaises(ValueError):p.acknowledge(self.root,'12345678','wrong')
        self.assertIn('inflight',self.state())


class PayloadTests(unittest.TestCase):
    def test_order_and_incidental_check_timestamp_ignored(self):
        a=[{'system':'ci','type':'x','status':'success','updated_at':'1'},
           {'system':'ci','type':'y','status':'failure','updated_at':'2'}]
        b=copy.deepcopy(list(reversed(a)));b[0]['updated_at']='3'
        self.assertEqual(p.normalized_checks(a),p.normalized_checks(b))

    def test_missing_required_data_fails_closed(self):
        with self.assertRaises(ValueError):p.canonical({}, {}, [], [])
        with self.assertRaises(ValueError):p.normalized_comments([{'id':1}])

    def test_pagination_merges_and_rejects_partial(self):
        client=object.__new__(p.Arcanum)
        pages=iter([({'data':[{'id':1}]},{'link':'<https://arcanum.yandex.net/api/list?page=2>; rel="next"'}),
                    ({'data':[{'id':2}]},{'x-total-count':'2'})])
        client.page=lambda url:next(pages)
        self.assertEqual(client.get('/list',True),[{'id':1},{'id':2}])
        client.page=lambda url:({'data':[]},{'x-next-cursor':'opaque'})
        with self.assertRaises(ValueError):client.get('/list',True)

    def test_foreign_pagination_url_is_rejected_before_auth(self):
        client=object.__new__(p.Arcanum)
        with self.assertRaises(ValueError):client.page('https://evil.example/api/comments')

    def test_legacy_migration_detects_changes_without_schema_noise(self):
        snap=snapshot()
        legacy={'observed':{'head':'h1','base':'b1','merge':'m1'},
                'comments':[{'id':1,'text_sha256':snap['comments'][0]['text'],'status':'open'}],
                'checks':[{'system':'ci','type':'test','status':'success','system_check_id':'r1'}]}
        snap['checks'][0]['restartable'] = False  # Not recorded by old schema.
        self.assertEqual(p.legacy_comparison(snap,legacy),[])
        snap['comments'][0]['status']='resolved'
        self.assertEqual(p.legacy_comparison(snap,legacy),['comments'])




class CompactPollTests(PollFixture):
    def setUp(self):
        super().setUp()
        self.compact = {'version': 1, 'pr': {'updated_at': 't1'}, 'comments': []}
        p.atomic_json(self.root/'12345678/poll-state.json',
                      {'baseline': self.original, 'probe_signature':p.digest(self.compact),
                       'last_full_fetch_at':100})

    # Do not inherit the old baseline-only cases: exercise the two-stage path.
    def test_compact_unchanged_skips_full_snapshot_and_model(self):
        def no_full(_): raise AssertionError('Heavy endpoint called')
        outcome=p.process(self.config,self.root,no_full,self.send,now=1000,
                          probe=lambda _:self.compact)
        self.assertEqual(outcome,'unchanged-light')
        self.assertEqual(self.sent,[])

    def test_compact_change_loads_full_before_deciding(self):
        calls=[]
        full=copy.deepcopy(self.original);full['comments'][0]['status']='resolved'
        outcome=p.process(self.config,self.root,lambda _:calls.append(1) or full,self.send,
                          now=1000,probe=lambda _:{'version':1,'changed':True})
        self.assertEqual(outcome,'queued')
        self.assertEqual(calls,[1])
        self.assertEqual(len(self.sent),1)

    def test_timestamp_only_change_does_not_wake_model(self):
        outcome=p.process(self.config,self.root,lambda _:self.original,self.send,now=1000,
                          probe=lambda _:{'version':1,'timestamp':'new'})
        self.assertEqual(outcome,'unchanged')
        self.assertEqual(self.sent,[])

    def test_six_hour_reconciliation_detects_uncovered_change(self):
        full=copy.deepcopy(self.original);full['metadata']['summary']='Changed'
        outcome=p.process(self.config,self.root,lambda _:full,self.send,now=22000,
                          probe=lambda _:self.compact)
        self.assertEqual(outcome,'queued')

    def test_no_remote_reads_while_event_is_inflight(self):
        state=self.state();state['inflight']={'event_id':'pending','status':'queued'}
        p.atomic_json(self.root/'12345678/poll-state.json',state)
        def forbidden(_):raise AssertionError('Remote read during inflight')
        self.assertEqual(p.process(self.config,self.root,forbidden,self.send,now=1000,
                                   probe=forbidden),'awaiting-ack')

    def test_429_retry_after_survives_force_and_keeps_baseline(self):
        def fail(_):raise p.HTTPFailure(429,'7200')
        self.assertEqual(p.process(self.config,self.root,fail,self.send,now=1000),
                         'fetch-error:HTTPFailure')
        self.assertGreaterEqual(self.state()['retry_not_before'],8200)
        self.assertEqual(p.process(self.config,self.root,fail,self.send,now=1100,force=True),'backoff')
        self.assertEqual(self.state()['baseline'],self.original)
        self.assertEqual(self.sent,[])

    def test_transient_failures_increase_delay(self):
        def fail(_):raise TimeoutError()
        p.process(self.config,self.root,fail,self.send,now=1000)
        first=self.state()['next_poll_at']
        p.process(self.config,self.root,fail,self.send,now=first)
        self.assertEqual(self.state()['next_poll_at']-first,1800)


class GovernorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.now=[10000]
        self.g=p.RequestGovernor(self.root,minimum_gap=0,hourly_limit=2,clock=lambda:self.now[0])

    def test_hourly_budget_shared_by_instances(self):
        self.g.before_request();self.g.before_request()
        other=p.RequestGovernor(self.root,minimum_gap=0,hourly_limit=2,clock=lambda:self.now[0])
        with self.assertRaises(p.Deferred):other.before_request()
        self.now[0]+=3601
        other.before_request()

    def test_global_server_cooldown_applies_to_next_pr(self):
        self.g.failed(p.HTTPFailure(429,'7200'))
        other=p.RequestGovernor(self.root,minimum_gap=0,clock=lambda:self.now[0])
        with self.assertRaises(p.Deferred) as error:other.before_request()
        self.assertEqual(error.exception.retry_at,17200)

    def test_retry_after_http_date_and_invalid_value(self):
        from email.utils import formatdate
        self.assertEqual(p.retry_after_seconds(formatdate(11000,usegmt=True),10000),1000)
        self.assertEqual(p.retry_after_seconds('garbage',10000),0)
        self.assertEqual(p.retry_after_seconds('-1',10000),0)

    def test_minimum_gap_enforced_between_requests(self):
        slept=[]
        def sleep(delay):slept.append(delay);self.now[0]+=delay
        g=p.RequestGovernor(self.root,minimum_gap=2,clock=lambda:self.now[0],sleep=sleep)
        g.before_request();g.before_request()
        self.assertEqual(slept,[2])


class ProbeSchemaTests(unittest.TestCase):
    def test_two_small_endpoints_no_comment_content(self):
        calls=[]
        def get(path,collection=False):
            calls.append(path)
            if collection:
                return [{'id':1,'is_draft':False,'updated_at':'t','thread_updated_at':'t','issue_status':'open'}]
            return {'id':12345678,'updated_at':'t','state':'open','full_status':'open','approvers':[],
                    'active_diff_set':{'id':1,'patch_vcs_ids':{'arc_branch_heads':
                        {'from_id':'h','to_id':'b','merge_id':'m'}}},
                    'checks':[{'system':'ci','type':'test','status':'success','updated_at':'c'}]}
        client=object.__new__(p.Arcanum);client.get=get
        result=client.probe('12345678')
        self.assertEqual(len(calls),2)
        self.assertNotIn('content',calls[1])
        self.assertEqual(result['comments'][0]['issue_status'],'open')

    def test_missing_fields_does_not_silently_fallback_to_heavy_poll(self):
        client=object.__new__(p.Arcanum)
        client.get=lambda path,collection=False:[] if collection else {'id':12345678}
        with self.assertRaises(ValueError):client.probe('12345678')


class StatusTests(unittest.TestCase):
    def test_cli_json_compatibility_and_human_output_without_network_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            monitors = [{'pr_id': '12345678', 'interval_seconds': 900,
                         'skill_path': '/skills/arcanum-pr-agent-helper/SKILL.md'},
                        {'pr_id': '12345679', 'interval_seconds': 600,
                         'skill_path': '/skills/arcanum-auto-review/SKILL.md'}]
            stopped = {'stopped': True, 'last_checked_at': 1000,
                       'next_poll_at': 2000, 'baseline': {'metadata': {'summary': 'Saved PR'}}}
            p.atomic_json(root/'config.json', {'monitors': monitors})
            p.atomic_json(root/'12345678/poll-state.json', stopped)
            command = [sys.executable, str(Path(p.__file__).resolve()),
                       '--root', str(root), 'status']
            before = {str(f): f.read_bytes() for f in root.rglob('*') if f.is_file()}
            raw = subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual([json.loads(line) for line in raw.stdout.splitlines()],
                             [{'pr': '12345678', 'interval': 900, 'title': 'Saved PR', 'stopped': True,
                               'author': None, 'stop_reason': 'unknown',
                               'last_checked_at': 1000, 'next_poll_at': 2000,
                               'skill': 'arcanum-pr-agent-helper', 'mode': 'PR agent helper'},
                              {'pr': '12345679', 'interval': 600, 'title': None, 'author': None,
                               'skill': 'arcanum-auto-review', 'mode': 'Auto review'}])
            human = subprocess.run(command + ['--human'], check=True, capture_output=True, text=True)
            self.assertIn('Остановлен', human.stdout)
            self.assertIn('Ожидает первого опроса', human.stdout)
            self.assertIn('15 мин', human.stdout)
            self.assertIn('Saved PR', human.stdout)
            self.assertIn('PR agent helper', human.stdout)
            self.assertIn('Auto review', human.stdout)
            self.assertNotIn('baseline', human.stdout)
            self.assertEqual(before, {str(f): f.read_bytes() for f in root.rglob('*') if f.is_file()})

    def test_mode_uses_current_skill_path_not_interval_or_legacy_state(self):
        helper = {'skill_path': '/skills/arcanum-pr-agent-helper/SKILL.md',
                  'interval_seconds': 900, 'review_state': '/old/arcanum-auto-review/state.json'}
        review = {'skill_path': '/skills/arcanum-auto-review/SKILL.md',
                  'interval_seconds': 600, 'review_state': '/old/arcanum-review-watch/state.json'}
        self.assertEqual(p.monitor_mode(helper), 'PR agent helper')
        self.assertEqual(p.monitor_mode(review), 'Auto review')
        self.assertIsNone(p.monitor_mode({}))
        self.assertEqual(p.monitor_mode({'skill_path': '/skills/custom/SKILL.md'}), 'custom')

    def test_human_title_does_not_inject_lines_or_terminal_escapes(self):
        state = {'title': 'Title\nwith\tspacing\x1b[31m'}
        output = p.human_status([{'pr_id': '12345678', 'interval_seconds': 600}], [state])
        self.assertNotIn('\x1b', output)
        self.assertIn('Title with spacing[31m', output)
        self.assertEqual(state['title'], 'Title\nwith\tspacing\x1b[31m')

    def test_status_precedence_and_no_obsolete_scheduled_time(self):
        monitors = [{'pr_id': str(pr), 'interval_seconds': 600} for pr in range(1, 5)]
        states = [{'inflight': {'status': 'queued', 'event_id': 'event-one'}, 'next_poll_at': 10},
                  {'inflight': {'status': 'uncertain', 'event_id': 'event-two'}},
                  {'last_error': 'HTTPFailure', 'last_http_status': 429, 'retry_not_before': 5000},
                  {'stopped': True, 'inflight': {'status': 'queued'}, 'next_poll_at': 10}]
        output = p.human_status(monitors, states, now=1000)
        self.assertIn('Ждёт завершения ревью', output)
        self.assertIn('Доставка не подтверждена', output)
        self.assertIn('Пауза перед повтором', output)
        self.assertIn('HTTP 429', output)
        self.assertIn('event-one', output)
        stopped = next(line for line in output.splitlines() if line.startswith('4 '))
        self.assertIn('Остановлен', stopped)
        self.assertNotIn('после подтверждения', stopped)
        self.assertEqual(p.human_status([], []), 'Нет зарегистрированных PR.')

    def test_author_and_stop_reason_display(self):
        monitors = [{'pr_id': str(i), 'interval_seconds': 600} for i in range(1, 4)]
        states = [{'stopped': True, 'stop_reason': 'author_ship', 'author': {'name': 'alice'}},
                  {'stopped': True, 'stop_reason': 'merged', 'author': {'uid': 123456}},
                  {'stopped': True}]
        output = p.human_status(monitors, states)
        self.assertIn('Автор', output)
        self.assertIn('alice', output)
        self.assertIn('123456', output)
        self.assertIn('Остановлен (ship автора)', output)
        self.assertIn('Остановлен (PR влит)', output)
        self.assertIn('Остановлен (причина не сохранена)', output)
        self.assertEqual(p.author_label({'login': 'login', 'name': 'Name', 'uid': 1}), 'login')

    def test_legacy_stop_requires_matching_event_and_preserves_explicit_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = root/'review.json'
            monitor = {'pr_id': '12345678', 'review_state': str(review)}
            state_path = root/'12345678/poll-state.json'
            state = {'stopped': True, 'last_ack': {'event_id': 'current'},
                     'baseline': {'metadata': {'author': {'name': 'alice'}}}}
            p.atomic_json(state_path, state)
            p.atomic_json(review, {'terminal': {'reason': 'author_ship', 'event_id': 'current'}})
            loaded = p.load_status_state(root, monitor)
            self.assertEqual(loaded['stop_reason'], 'author_ship')
            self.assertEqual(loaded['author'], {'name': 'alice'})
            self.assertEqual(p.read_json(state_path), state)  # status remains read-only
            p.atomic_json(review, {'terminal': {'reason': 'author_ship', 'event_id': 'old'}})
            self.assertEqual(p.load_status_state(root, monitor)['stop_reason'], 'unknown')
            state['stop_reason'] = 'user_request'
            p.atomic_json(state_path, state)
            self.assertEqual(p.load_status_state(root, monitor)['stop_reason'], 'user_request')

    def test_stop_cli_saves_reason_and_resume_clears_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p.atomic_json(root/'config.json', {'monitors': []})
            command = [sys.executable, str(Path(p.__file__).resolve()), '--root', str(root)]
            subprocess.run(command + ['stop', '--pr', '12345678', '--reason', 'author_ship'],
                           check=True, capture_output=True)
            state_path = root/'12345678/poll-state.json'
            self.assertEqual(p.read_json(state_path)['stop_reason'], 'author_ship')
            subprocess.run(command + ['resume', '--pr', '12345678'], check=True, capture_output=True)
            self.assertFalse(p.read_json(state_path)['stopped'])
            self.assertNotIn('stop_reason', p.read_json(state_path))
            subprocess.run(command + ['stop', '--pr', '12345678'], check=True, capture_output=True)
            self.assertEqual(p.read_json(state_path)['stop_reason'], 'user_request')


class StopAckTests(PollFixture):
    def test_stop_ack_saves_reason_and_author_once(self):
        changed = copy.deepcopy(self.original)
        changed['metadata']['status'] = 'merged'
        self.run_poll(changed, now=0)
        event = self.sent[-1]['id']
        p.acknowledge(self.root, '12345678', event, stop=True, reason='merged')
        self.assertEqual(self.state()['stop_reason'], 'merged')
        self.assertEqual(self.state()['author'], {'name': 'author'})
        self.assertTrue(self.state()['stopped'])
        self.assertEqual(p.acknowledge(self.root, '12345678', event, stop=True, reason='merged'),
                         'already-acked')
        with self.assertRaises(ValueError):
            p.acknowledge(self.root, '12345678', event, reason='merged')


if __name__ == "__main__":
    unittest.main()
