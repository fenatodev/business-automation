# WP-048 — Provision local n8n review Data Table only

Status: authorized local provisioning of the single new Data Table. No credentials or workflow mutations.

## Verified context
- n8n 2.40.7 private UI reachable through the Docker bridge.
- API key file is local: `~/.config/business-automation/n8n-api-key` (mode 0600).
- Local API probe confirmed GET `/api/v1/credentials?limit=1` and GET `/api/v1/data-tables?limit=1` return HTTP 200.
- Target workflow ID: `99999999-9999-4999-8999-999999999999` (inactive).
- Canonical schema source: `ops/n8n/workflows/client0-commercial-intake-review.json`, node `Queue for Human Review`.

## Task
1. Clone exact handoff commit in a **fresh** temporary directory; read `AGENTS.md` and this file. Create branch `wp/048-n8n-data-table-provision`.
2. Resolve current n8n container IP via `docker inspect`. Read API key in process memory only; never log, print, export, persist in shell history or commit it.
3. Read **metadata only** from GET `/api/v1/data-tables` (paginate if necessary), inspect whether `client0_commercial_review_queue` already exists. If it exists, check column names/types without reading rows; if schema matches, report ALREADY_PRESENT and do nothing. If an existing table has different schema, STOP: no replacement.
4. If absent, verify exact public API request schema from installed n8n 2.40.7 documentation/OpenAPI (do not guess a payload). Then create only this Data Table, with exact columns:
   - `event_id`: string
   - `status`: string
   - `intent`: string
   - `draft_reply`: string
   - `needs_human_review`: boolean
   - `flags_json`: string
   - `received_at`: dateTime
   Check that types are accepted by this n8n version. Do **not** silently map unsupported types; STOP with blocker if exact representation is unclear.
5. Read back the created table's *schema metadata* (no rows), verify exactly 7 columns. Do not reissue POST after uncertain result; GET before any retry.
6. Write only `docs/operations/wp-048-n8n-data-table-report.md` containing sanitized PASS/FAIL, exact base SHA, table name, actual column names/types, HTTP status codes, and blockers. Never publish private IP, auth tokens, API bodies, client data or table rows.
7. `git diff --check`; commit and push only report on WP branch; no merge; STOP.

## Strict prohibitions
No credential creation/import/export, workflow edits/import/activation/execution, webhook calls, FastAPI/Ollama startup, Docker mutations, n8n DB/SQLite inspection, migrations, secrets in Git, external paid API, arbitrary network traffic, or other WPs.
Never use n8n internal DB writes or unverified endpoints as a workaround. On 401/403/404 or schema incompatibility, STOP. No destructive actions.
