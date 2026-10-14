# WP-047 — n8n private UI bootstrap preflight

Status: **read-only and user-action gate**.

## Verified (2026-10-14)
- WP-046 report: workflow ID `99999999-9999-4999-8999-999999999999` updated with private URL and inactive; credentials and Data Table still absent.
- Separate Desktop Commander read-only check: HTTP **200** from Ubuntu host to n8n container bridge IP on port 5678. No host port publication, restart, proxy or network mutation required. Inactive workflow ID independently confirmed.
- The WP-046 report describes direct inspection of n8n internal SQLite tables and re-import as a 'collision test'. **Do not repeat these operations**. Database introspection exceeded the narrow metadata-only authorization, and direct credential import/DB mutation is not approved.

## Gate
Only the authorized operator may finish n8n owner account setup in its existing UI, then create a scoped API key or manage credentials via UI. Do not assume unauthenticated API availability or bypass user setup. No credentials should be sent to the chat/GitHub.

## Safe local preflight
1. Read `AGENTS.md`; in a new temporary clone at exact handoff SHA, create `wp/047-n8n-private-ui-preflight`.
2. Read-only inspect n8n container bridge IP via Docker metadata and test `GET /` from host with curl. Report status only, never publish the private IP in GitHub reports.
3. Confirm target workflow ID remains listed by CLI as inactive. Do not read workflow bodies or secrets.
4. Report the safe UI-access method **locally to the user** (a bridge IP reachable from host), but do not create/start reverse proxies or publish ports.
5. Record `PASS/FAIL` and blockers in `docs/operations/wp-047-n8n-private-ui-report.md` and push branch. STOP.

## Forbidden
No database inspection (including SQLite/WAL copies or SQL), credential import/export, creating API keys, account initialization on user's behalf, n8n workflow import/update/activation, Data Table mutation, Docker config/network/port changes, service restart, starting API, model calls, paid service, migration, webhook execution or outbound sends. Never request/share secret values.
