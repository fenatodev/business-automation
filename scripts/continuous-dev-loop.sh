#!/usr/bin/env bash
set -Eeuo pipefail

WORKTREE="${BA_CONTINUOUS_WORKTREE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOG_DIR="${BA_CONTINUOUS_LOG_DIR:-/tmp/business-automation-codex-loop}"
STOP_FILE="${BA_CONTINUOUS_STOP_FILE:-/tmp/business-automation.stop}"
TASK_FILE="${BA_CONTINUOUS_TASK_FILE:-$WORKTREE/scripts/continuous-dev-task.md}"
INTERVAL="${BA_CONTINUOUS_INTERVAL:-20}"
MAX_BACKOFF="${BA_CONTINUOUS_MAX_BACKOFF:-300}"
CODEX_BIN="${BA_CODEX_BIN:-codex}"

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
  command -v gh >/dev/null || { log "BLOCKED: GitHub CLI not found"; return 1; }
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
  gh pr list --state open --limit 100 --json headRefName \
    --jq '.[] | select(.headRefName | startswith("wp/")) | .headRefName'
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

run_codex() {
  log "START: independent Codex execution"
  if ((DRY_RUN)); then
    log "DRY-RUN: would execute Codex with $TASK_FILE"
    return 0
  fi
  "$CODEX_BIN" exec --ephemeral --sandbox danger-full-access \
    -c 'approval_policy="never"' -C "$WORKTREE" \
    -o "$LOG_DIR/$RUN_ID.last-message.txt" < "$TASK_FILE"
}

main() {
  require_tools || exit 2
  if stop_requested; then log "STOP: stop file exists: $STOP_FILE"; exit 0; fi
  prepare_main || exit 3
  run_codex || { log "BLOCKED: Codex execution failed; no retry in this run"; exit 4; }
  if [[ -n "$(open_agent_prs)" ]]; then
    log "BLOCKED: execution ended with an open agent PR; wait for CI/merge"
    open_agent_prs
    exit 5
  fi
  log "PASS: execution ended without an open agent PR"
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
    log "WAIT: retrying after ${backoff}s unless stopped"
    sleep "$backoff"
    next=$((backoff * 2))
    (( next < backoff )) && next="$MAX_BACKOFF"
    (( next > MAX_BACKOFF )) && next="$MAX_BACKOFF"
    backoff="$next"
  fi
done
