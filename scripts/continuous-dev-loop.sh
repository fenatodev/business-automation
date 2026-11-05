#!/usr/bin/env bash
set -Eeuo pipefail

WORKTREE="${BA_CONTINUOUS_WORKTREE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOG_DIR="${BA_CONTINUOUS_LOG_DIR:-/tmp/business-automation-codex-loop}"
STOP_FILE="${BA_CONTINUOUS_STOP_FILE:-/tmp/business-automation.stop}"
TASK_FILE="${BA_CONTINUOUS_TASK_FILE:-$WORKTREE/scripts/continuous-dev-task.md}"
INTERVAL="${BA_CONTINUOUS_INTERVAL:-20}"
MAX_BACKOFF="${BA_CONTINUOUS_MAX_BACKOFF:-300}"
CODEX_BIN="${BA_CODEX_BIN:-codex}"
GH_BIN="${BA_GH_BIN:-gh}"

usage() {
  cat <<'EOF'
Usage: scripts/continuous-dev-loop.sh [--once] [--dry-run]

Runs one independent Codex execution per safe work package. Logs stay outside
the repository. The loop stops on /tmp/business-automation.stop, a dirty
worktree, an open agent PR, or a real blocking condition.
EOF
}

ONCE=0
DRY_RUN=0
while (($#)); do
  case "$1" in
    --once) ONCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 64 ;;
  esac
done

mkdir -p "$LOG_DIR"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
RUN_LOG="$LOG_DIR/$RUN_ID.log"
exec > >(tee -a "$RUN_LOG") 2>&1

stop_requested() { [[ -e "$STOP_FILE" ]]; }
log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }

on_signal() {
  log "STOP: received interrupt; preserving worktree and logs"
  exit 130
}
trap on_signal INT TERM

require_tools() {
  command -v "$CODEX_BIN" >/dev/null || { log "BLOCKED: Codex CLI not found"; return 1; }
  command -v git >/dev/null || { log "BLOCKED: git not found"; return 1; }
  command -v "$GH_BIN" >/dev/null || { log "BLOCKED: GitHub CLI not found"; return 1; }
  command -v jq >/dev/null || { log "BLOCKED: jq not found"; return 1; }
  [[ -f "$TASK_FILE" ]] || { log "BLOCKED: task file missing: $TASK_FILE"; return 1; }
}

worktree_clean() {
  local changes
  changes="$(git -C "$WORKTREE" status --porcelain=v1)"
  if [[ -n "$changes" ]]; then
    log "BLOCKED: worktree has unexpected local changes"
    printf '%s\n' "$changes"
    return 1
  fi
}

open_agent_prs() {
  "$GH_BIN" pr list --state open --limit 100 --json number,title,headRefName,headRefOid \
    --jq '.[] | select(.headRefName | startswith("wp/"))'
}

prepare_main() {
  worktree_clean || return 1
  local branch
  branch="$(git -C "$WORKTREE" branch --show-current)"
  [[ "$branch" == "main" ]] || { log "BLOCKED: worktree is on $branch, expected main"; return 1; }
  git -C "$WORKTREE" fetch origin
  git -C "$WORKTREE" pull --ff-only origin main
  worktree_clean || return 1
  if [[ -n "$(open_agent_prs)" ]]; then
    log "BLOCKED: an agent WP PR is already open"
    open_agent_prs
    return 1
  fi
}

pr_risk_reason() {
  local number="$1" title body files
  title="$("$GH_BIN" pr view "$number" --json title --jq '.title')"
  body="$("$GH_BIN" pr view "$number" --json body --jq '.body')"
  files="$("$GH_BIN" pr diff "$number" --name-only)"
  if printf '%s\n%s\n%s\n' "$title" "$body" "$files" | grep -Eiq \
    'migration|alembic|auth(entication|orization)?|rbac|security|contract|docker|compose|deploy|cloudflare|vps|n8n|credential|secret|\.env|\.pem|\.key|integration'; then
    printf '%s\n' "high-risk PR #$number ($title)"
    return 0
  fi
  return 1
}

sync_main_after_merge() {
  git -C "$WORKTREE" fetch origin
  git -C "$WORKTREE" switch main
  git -C "$WORKTREE" pull --ff-only origin main
  worktree_clean
}

wait_for_ci() {
  local number="$1" checks pending failures
  while :; do
    stop_requested && { log "STOP: stop file requested while waiting for CI"; return 130; }
    checks="$("$GH_BIN" pr view "$number" --json statusCheckRollup)" || {
      log "BLOCKED: unable to read CI status for PR #$number"
      return 1
    }
    pending="$(printf '%s' "$checks" | jq '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length')"
    failures="$(printf '%s' "$checks" | jq '[.statusCheckRollup[] | select(.status == "COMPLETED" and ((.conclusion // "") | IN("FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED")))] | length')"
    if (( failures > 0 )); then
      log "BLOCKED: CI failed for PR #$number"
      printf '%s\n' "$checks" | jq -r '.statusCheckRollup[] | [.name, .status, (.conclusion // ""), (.detailsUrl // "")] | @tsv'
      return 1
    fi
    if (( pending == 0 )); then
      if [[ "$(printf '%s' "$checks" | jq '.statusCheckRollup | length')" == "0" ]]; then
        log "BLOCKED: PR #$number has no reported checks"
        return 1
      fi
      log "CI PASS: all checks completed for PR #$number"
      return 0
    fi
    log "WAIT: PR #$number has $pending pending check(s)"
    sleep 10
  done
}

merge_agent_pr() {
  local prs count number branch expected_sha current_sha review merge_status checks_output
  prs="$(open_agent_prs)"
  count="$(printf '%s\n' "$prs" | jq -s 'length')"
  if [[ "$count" != "1" ]]; then
    if [[ "$count" == "0" ]]; then
      log "BLOCKED: Codex ended without exactly one open WP PR"
    else
      log "BLOCKED: multiple open WP PRs; refusing to choose"
      printf '%s\n' "$prs"
    fi
    return 10
  fi

  number="$(printf '%s\n' "$prs" | jq -r '.number')"
  branch="$(printf '%s\n' "$prs" | jq -r '.headRefName')"
  expected_sha="$(printf '%s\n' "$prs" | jq -r '.headRefOid')"
  log "PR #$number branch=$branch head=$expected_sha"

  if pr_risk_reason "$number"; then
    log "BLOCKED: PR requires human review because it matches a protected scope"
    return 10
  fi

  review="$("$GH_BIN" pr view "$number" --json reviewDecision --jq '.reviewDecision // ""')"
  merge_status="$("$GH_BIN" pr view "$number" --json mergeStateStatus --jq '.mergeStateStatus // ""')"
  if [[ "$review" == "CHANGES_REQUESTED" || "$review" == "REVIEW_REQUIRED" || "$merge_status" == "BLOCKED" ]]; then
    log "BLOCKED: PR #$number requires human review (review=$review merge=$merge_status)"
    return 10
  fi

  log "WAIT: watching CI for PR #$number"
  local ci_code=0
  if wait_for_ci "$number"; then
    ci_code=0
  else
    ci_code=$?
  fi
  if (( ci_code == 130 )); then
    return 130
  fi
  if (( ci_code != 0 )); then
    return 10
  fi

  current_sha="$("$GH_BIN" pr view "$number" --json headRefOid --jq '.headRefOid')"
  if [[ "$current_sha" != "$expected_sha" ]]; then
    log "BLOCKED: PR #$number head changed from $expected_sha to $current_sha"
    return 10
  fi

  log "MERGE: merging PR #$number normally"
  if ! "$GH_BIN" pr merge "$number" --merge --delete-branch=false; then
    log "BLOCKED: normal merge failed for PR #$number; human action may be required"
    return 10
  fi
  local state
  state="$("$GH_BIN" pr view "$number" --json state --jq '.state')"
  [[ "$state" == "MERGED" ]] || { log "BLOCKED: PR #$number did not reach MERGED state"; return 10; }
  sync_main_after_merge
  log "PASS: PR #$number merged and main synchronized"
}

run_codex() {
  log "START: independent Codex execution"
  if ((DRY_RUN)); then
    log "DRY-RUN: would execute Codex with $TASK_FILE"
    return 0
  fi
  "$CODEX_BIN" exec --ephemeral --ignore-user-config --sandbox danger-full-access \
    -c 'approval_policy="never"' -C "$WORKTREE" \
    -o "$LOG_DIR/$RUN_ID.last-message.txt" < "$TASK_FILE"
}

main() {
  require_tools || exit 2
  if stop_requested; then log "STOP: stop file exists: $STOP_FILE"; exit 0; fi
  prepare_main || exit 3
  run_codex || { log "BLOCKED: Codex execution failed; no retry in this run"; exit 4; }
  merge_agent_pr || exit $?
}

if ((ONCE)); then
  main
  exit $?
fi

backoff="$INTERVAL"
while :; do
  stop_requested && { log "STOP: stop file exists: $STOP_FILE"; exit 0; }
  if main; then
    backoff="$INTERVAL"
  else
    code=$?
    (( code == 130 )) && { log "STOP: interrupted while waiting"; exit 130; }
    (( code == 10 )) && { log "STOP: terminal BLOCKED state"; exit 10; }
    log "WAIT: retrying after ${backoff}s unless stopped"
    sleep "$backoff"
    next=$((backoff * 2))
    (( next < backoff )) && next="$MAX_BACKOFF"
    (( next > MAX_BACKOFF )) && next="$MAX_BACKOFF"
    backoff="$next"
  fi
done
