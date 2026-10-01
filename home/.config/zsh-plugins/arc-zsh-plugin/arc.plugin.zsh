# Arc plugin for Oh My Zsh
# Provides prompt functions for Arc VCS
# Similar to the built-in git plugin

zmodload zsh/datetime

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

# Prompt prefix/suffix
: ${ARC_PROMPT_PREFIX:="%{$fg_bold[blue]%}arc:(%{$fg[red]%}"}
: ${ARC_PROMPT_SUFFIX:="%{$fg_bold[blue]%})%{$reset_color%}"}

# Status symbols
: ${ARC_PROMPT_DIRTY:=" %{$fg[yellow]%}✗%{$reset_color%}"}
: ${ARC_PROMPT_CLEAN:=" %{$fg[green]%}✔%{$reset_color%}"}
: ${ARC_PROMPT_STAGED:=" %{$fg[green]%}●%{$reset_color%}"}
: ${ARC_PROMPT_UNTRACKED:=" %{$fg[cyan]%}?%{$reset_color%}"}
: ${ARC_PROMPT_CONFLICTS:=" %{$fg[red]%}✖%{$reset_color%}"}

# Cache settings (arc can be slow in large repos)
: ${ARC_STATUS_CACHE_TIMEOUT:=2}  # seconds

# ------------------------------------------------------------------------------
# Internal cache variables
# ------------------------------------------------------------------------------

_arc_status_cache=""
_arc_status_cache_time=0
_arc_repo_root_cache=""
_arc_last_pwd=""

# Parsed status counters
_arc_staged=0
_arc_unstaged=0
_arc_untracked=0
_arc_conflicts=0

# HEAD state (set by _arc_read_head)
_arc_head_type=""
_arc_head_value=""

# ------------------------------------------------------------------------------
# Core Functions
# ------------------------------------------------------------------------------

# Check if current directory is inside an arc repository
function arc_is_repo() { [[ -n "$(arc_repo_root)" ]] }

# Get the repository root path
function arc_repo_root() {
  if [[ "$PWD" != "$_arc_last_pwd" ]]; then
    _arc_repo_root_cache=""
    _arc_last_pwd="$PWD"
  fi

  if [[ -z "$_arc_repo_root_cache" ]]; then
    _arc_repo_root_cache=$(command arc root 2>/dev/null)
  fi
  echo "$_arc_repo_root_cache"
}

# Parse .arc/HEAD → sets _arc_head_type and _arc_head_value globals
function _arc_read_head() {
  local head_content
  head_content=$(<"$1/HEAD" 2>/dev/null) || { _arc_head_type=""; _arc_head_value=""; return 1; }

  if [[ "$head_content" =~ 'Symbolic: "([^"]+)"' ]]; then
    _arc_head_type="branch"
    _arc_head_value="${match[1]}"
  elif [[ "$head_content" =~ 'Id: "([^"]+)"' ]]; then
    _arc_head_type="detached"
    _arc_head_value="${match[1]}"
  else
    _arc_head_type=""
    _arc_head_value=""
    return 1
  fi
}

# Check if branch has a remote tracking ref
function _arc_has_remote() { [[ -f "$1/refs/remotes/arcadia/$2" ]] }

# Shorten a branch name for display
function _arc_short_branch() {
  local branch="$1"
  if [[ "$branch" =~ ^users/[^/]+/(.+)$ ]]; then
    echo "${match[1]}"
  else
    echo "$branch"
  fi
}

# Get the current branch name for display (also sets _arc_head_type/_arc_head_value)
function arc_current_branch() {
  local arc_dir="$(arc_repo_root)/.arc"
  _arc_read_head "$arc_dir" || return

  if [[ "$_arc_head_type" == "branch" ]]; then
    _arc_short_branch "$_arc_head_value"
    return
  fi

  # Detached HEAD — check if we're mid-operation and return the original branch
  local seq_file="$arc_dir/sequencer/commits"
  if [[ -f "$seq_file" ]]; then
    local branch_line
    branch_line=$(command grep -m1 'BranchName:' "$seq_file" 2>/dev/null)
    if [[ "$branch_line" =~ '"([^"]+)"' ]]; then
      _arc_short_branch "${match[1]}"
      return
    fi
  fi

  # Truly detached — return empty (callers handle this via _arc_head_type/_arc_head_value)
}

# ------------------------------------------------------------------------------
# Status Functions (with caching)
# ------------------------------------------------------------------------------

# Refresh cached status and parse counters
function _arc_refresh_status() {
  local current_time=$EPOCHSECONDS
  local cache_age=$((current_time - _arc_status_cache_time))

  if [[ $cache_age -gt $ARC_STATUS_CACHE_TIMEOUT ]] || [[ -z "$_arc_status_cache" ]]; then
    _arc_status_cache=$(command arc status --short 2>/dev/null)
    _arc_status_cache_time=$current_time

    # Reset counters
    _arc_staged=0
    _arc_unstaged=0
    _arc_untracked=0
    _arc_conflicts=0

    # Parse status lines
    local line
    for line in ${(f)_arc_status_cache}; do
      [[ -z "$line" ]] && continue
      local x="${line[1]}"
      local y="${line[2]}"

      # Conflicts: UU, AA, DD, UA, AU, DU, UD
      if [[ "$x" == U || "$y" == U || ( "$x" == A && "$y" == A ) || ( "$x" == D && "$y" == D ) ]]; then
        (( _arc_conflicts++ ))
        continue
      fi

      # Untracked
      if [[ "$x" == '?' ]]; then
        (( _arc_untracked++ ))
        continue
      fi

      # Staged (first column)
      if [[ "$x" == [MADRC] ]]; then
        (( _arc_staged++ ))
      fi

      # Unstaged (second column)
      if [[ "$y" == [MADRC] ]]; then
        (( _arc_unstaged++ ))
      fi
    done
  fi
}

# Boolean accessors
function arc_has_staged()    { _arc_refresh_status; (( _arc_staged > 0 )); }
function arc_has_unstaged()  { _arc_refresh_status; (( _arc_unstaged > 0 )); }
function arc_has_untracked() { _arc_refresh_status; (( _arc_untracked > 0 )); }
function arc_has_conflicts() { _arc_refresh_status; (( _arc_conflicts > 0 )); }

# Check if repo is dirty (any uncommitted changes: staged, unstaged, or untracked)
function arc_is_dirty() {
  _arc_refresh_status
  (( _arc_staged + _arc_unstaged + _arc_untracked > 0 ))
}

# ------------------------------------------------------------------------------
# Operation State Detection
# ------------------------------------------------------------------------------

# Detect in-progress operations (rebase, merge, cherry-pick, revert)
function _arc_operation_mode() {
  local seq_file="$1/sequencer/commits"
  [[ -f "$seq_file" ]] || return

  local type_line
  type_line=$(command grep -m1 '^Type:' "$seq_file" 2>/dev/null) || return

  case "$type_line" in
    *TypeRebase*)      echo ">R>" ;;
    *TypeCherryPick*)  echo ">C<" ;;
    *TypeRevert*)      echo ">V<" ;;
    *TypeMerge*)       echo ">M<" ;;
  esac
}

# ------------------------------------------------------------------------------
# Prompt Functions
# ------------------------------------------------------------------------------

# Main prompt info function - similar to git_prompt_info()
function arc_prompt_info() {
  local root
  root=$(arc_repo_root)
  [[ -n "$root" ]] || return

  local arc_dir="$root/.arc"
  local branch ref
  branch=$(arc_current_branch)

  if [[ -n "$branch" ]]; then
    ref="$branch"
  else
    # Detached HEAD — show short commit hash
    [[ "$_arc_head_type" == "detached" ]] || return
    ref="➦ ${_arc_head_value[1,8]}"
  fi

  _arc_refresh_status

  local indicators=""

  if (( _arc_conflicts > 0 )); then
    indicators+="$ARC_PROMPT_CONFLICTS"
  fi

  if (( _arc_staged > 0 )); then
    indicators+="$ARC_PROMPT_STAGED"
  fi

  if (( _arc_unstaged > 0 )); then
    indicators+="$ARC_PROMPT_DIRTY"
  fi

  if (( _arc_untracked > 0 )); then
    indicators+="$ARC_PROMPT_UNTRACKED"
  fi

  if [[ -z "$indicators" ]]; then
    indicators="$ARC_PROMPT_CLEAN"
  fi

  local mode=$(_arc_operation_mode "$arc_dir")

  echo "${ARC_PROMPT_PREFIX}${ref}${ARC_PROMPT_SUFFIX}${indicators}${mode:+ $mode}"
}

# Short version - just branch name
function arc_prompt_short() {
  if ! arc_is_repo; then
    return
  fi

  local branch=$(arc_current_branch)
  if [[ -n "$branch" ]]; then
    echo " ($branch)"
  fi
}

# Detailed status for right prompt or status line
function arc_prompt_status() {
  if ! arc_is_repo; then
    return
  fi

  _arc_refresh_status

  local result=""
  [[ $_arc_staged -gt 0 ]] && result+="%{$fg[green]%}+${_arc_staged}%{$reset_color%} "
  [[ $_arc_unstaged -gt 0 ]] && result+="%{$fg[yellow]%}~${_arc_unstaged}%{$reset_color%} "
  [[ $_arc_untracked -gt 0 ]] && result+="%{$fg[cyan]%}?${_arc_untracked}%{$reset_color%}"

  echo "$result"
}

# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

# Clear the status cache (useful after arc operations)
function arc_clear_cache() {
  _arc_status_cache=""
  _arc_status_cache_time=0
  _arc_repo_root_cache=""
  _arc_staged=0
  _arc_unstaged=0
  _arc_untracked=0
  _arc_conflicts=0
  _arc_head_type=""
  _arc_head_value=""
}

# Hook to clear cache after arc commands and plugin aliases
function _arc_clear_cache_hook() {
  case "${1%% *}" in
    ar*) arc_clear_cache ;;
  esac
}

# Add hook to preexec
preexec_functions+=(_arc_clear_cache_hook)

# ------------------------------------------------------------------------------
# Agnoster theme integration
# ------------------------------------------------------------------------------

# Arc segment for agnoster theme (call this in build_prompt)
function prompt_arc() {
  # Skip if arc not available or not in arc repo
  (( $+commands[arc] )) || return

  local root
  root=$(arc_repo_root)
  [[ -n "$root" ]] || return

  local arc_dir="$root/.arc"
  local branch ref
  local PL_BRANCH_CHAR

  () {
    local LC_ALL="" LC_CTYPE="en_US.UTF-8"
    PL_BRANCH_CHAR=$'\ue0a0'  #
  }

  branch=$(arc_current_branch)

  if [[ -n "$branch" ]]; then
    # On a branch
    if [[ "$_arc_head_type" == "branch" ]] && ! _arc_has_remote "$arc_dir" "$_arc_head_value"; then
      # Local-only branch, not yet pushed — show ↑ icon
      PL_BRANCH_CHAR=$'\u21b1'  # ↱
    fi
    ref="${PL_BRANCH_CHAR} ${branch}"
  else
    # Detached HEAD — show short commit hash
    [[ "$_arc_head_type" == "detached" ]] || return
    ref="➦ ${_arc_head_value[1,8]}"
  fi

  # Use agnoster color settings (with arc-specific defaults)
  : ${AGNOSTER_ARC_CLEAN_FG:=${AGNOSTER_GIT_CLEAN_FG:-black}}
  : ${AGNOSTER_ARC_CLEAN_BG:=${AGNOSTER_GIT_CLEAN_BG:-green}}
  : ${AGNOSTER_ARC_DIRTY_FG:=${AGNOSTER_GIT_DIRTY_FG:-black}}
  : ${AGNOSTER_ARC_DIRTY_BG:=${AGNOSTER_GIT_DIRTY_BG:-yellow}}

  # Background color: yellow if any uncommitted changes, green if clean
  if arc_is_dirty; then
    prompt_segment "$AGNOSTER_ARC_DIRTY_BG" "$AGNOSTER_ARC_DIRTY_FG"
  else
    prompt_segment "$AGNOSTER_ARC_CLEAN_BG" "$AGNOSTER_ARC_CLEAN_FG"
  fi

  # Markers (mirrors git order: unstaged ±, staged ✚)
  local markers=""
  arc_has_unstaged && markers+="±"
  arc_has_staged && markers+="✚"

  local mode=$(_arc_operation_mode "$arc_dir")

  echo -n "${ref:gs/%/%%}${markers:+ $markers}${mode:+ $mode}"
}

# ------------------------------------------------------------------------------
# Agnoster auto-injection
# ------------------------------------------------------------------------------

# Automatically inject prompt_arc into agnoster's build_prompt after prompt_git.
# This makes the arc segment appear without manual .zshrc changes, just like git.
# Deferred via precmd because oh-my-zsh loads plugins before themes.
function _arc_inject_prompt() {
  if (( $+functions[build_prompt] )) && [[ "${functions[build_prompt]}" == *prompt_git* ]] \
     && [[ "${functions[build_prompt]}" != *prompt_arc* ]]; then
    functions[build_prompt]="${functions[build_prompt]/prompt_git/prompt_git
    prompt_arc}"
  fi
  # Run once then remove itself
  precmd_functions=(${precmd_functions:#_arc_inject_prompt})
  unfunction _arc_inject_prompt 2>/dev/null
}
precmd_functions+=(_arc_inject_prompt)

# ------------------------------------------------------------------------------
# Aliases (similar to git plugin)
# ------------------------------------------------------------------------------

alias arst='arc status'
alias arbr='arc branch'
alias arco='arc checkout'
alias arcob='arc checkout -b'
alias ardf='arc diff'
alias arlg='arc log'
alias arad='arc add'
alias arcm='arc commit -m'
alias arcam='arc commit -a -m'
alias arpl='arc pull'
alias arps='arc push'
alias arsb='arc submit'
alias arsbm='arc submit -m'
alias arrb='arc rebase'
alias arstash='arc stash push'
alias arstashp='arc stash pop'
