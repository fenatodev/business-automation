# Continuous development task

You are one independent local execution in `fenatodev/business-automation`.
Work only in `~/dev/worktrees/business-automation-next`; never use Cloud.

1. Verify the worktree and synchronize `main` with GitHub.
2. Read `AGENTS.md`, `docs/PRODUCT.md`, `docs/ROADMAP.md`,
   `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, relevant `docs/operations/`,
   and relevant `specs/`.
3. Inspect Issues, open PRs, branches, code, tests, and backlog.
4. Choose exactly one small, safe, functional WP. Do not start if local
   changes are unexpected or an agent PR is already open.
5. Create `wp/<id>-<description>` and implement one complete vertical slice.
6. Run `uv run pytest`, `.venv/bin/python -m compileall app tests`,
   `git diff --check`, and `scripts/preflight.sh` when present.
7. Inspect the diff for secrets, real data, migrations, credentials, external
   actions, or unrelated files.
8. Commit conventionally, push, and open exactly one PR. Leave the PR open for
   the supervisor to inspect; do not open a second WP or stop merely because
   the PR exists.
9. Report the PR number, branch, and head SHA, then finish this execution with
   exactly one status: `PR_READY`, `BLOCKED`, or `NO_SAFE_WP`. The supervisor
   waits for CI, verifies the head SHA, merges normal low-risk PRs, and
   synchronizes `main` before starting the next execution.

Never perform real migrations, use real PostgreSQL/customer data, activate
n8n, send messages, deploy, change DNS/Cloudflare/VPS, expose secrets, use
destructive Git commands, or delete unexpected user changes. If CI fails,
fix only a cause from this WP; otherwise record `BLOCKED` and stop.
