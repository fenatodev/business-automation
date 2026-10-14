# WP-043 — Validate restricted private intake ASGI (offline)

Base: exact main SHA provided in handoff.
Scope: local synthetic tests only; no Docker or API runtime.

1. Read AGENTS.md and this WP. Clone the repository into a fresh temporary directory at the exact supplied SHA. Create branch `wp/043-private-intake-validation`.
2. Run:
   - `uv run pytest -q tests/test_private_intake_entrypoint.py tests/test_private_api_bridge_artifacts.py`
   - `uv run pytest -q`
   - `uv run python -m compileall -q app tests`
   - `git diff --check`
3. Create only `docs/operations/wp-043-private-intake-validation-report.md` with PASS/FAIL, real test counts/exit codes, SHA, and blockers. Commit + push only the WP branch and STOP.

Do not change code/tests to force PASS. Do not access .env or live database, start containers/services, modify Docker/network/n8n, activate/import workflow, send anything, or run migrations. No merge; no other WP. If any command fails, record sanitized failure and STOP.
