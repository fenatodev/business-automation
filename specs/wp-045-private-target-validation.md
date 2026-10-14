# WP-045 — Validate private-target n8n workflow; keep inactive

## Preconditions
Use a fresh temporary clone of the exact main commit provided in the handoff. Read AGENTS.md. Branch: `wp/045-private-target-validation`.

## Scope
Offline tests and optional **inactive** import-only of `ops/n8n/workflows/client0-commercial-intake-review.json`. The workflow already exists in n8n from WP-040; the same top-level ID must be preserved. The URL now uses the WP-044-verified Docker alias `ba-intake-private`.

1. Run `uv run pytest -q tests/test_n8n_commercial_intake_workflow.py`, then `uv run pytest -q`, `uv run python -m compileall -q app tests`, and `git diff --check`. Record actual exit codes/count.
2. Check JSON contains exactly `"active": false`, the expected workflow ID `99999999-9999-4999-8999-999999999999`, and the private URL. If mismatch, STOP.
3. **Do not import/update the existing n8n workflow during this WP.** Imported inactive copy from WP-040 remains unchanged. A separate authorization will govern applying this updated JSON after tests.
4. Create only `docs/operations/wp-045-private-target-validation-report.md` with sanitized PASS/FAIL, SHA, real tests, noted blockers, confirmation of no runtime changes.
5. Commit/push the report branch, no PR merge, STOP.

Forbidden: start containers/API, modify n8n, import/activate/execute workflow, provision credential or Data Table, access env/secrets/real DB, migrations, messages, model calls, network changes, paid services, public ports, other WP.
