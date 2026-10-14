# WP-046 — n8n private integration readiness

Status: **prepared only; no execution authorized**.

Evidence: WP-040 imported an inactive workflow. WP-044 proved private DNS, TCP and HTTP 401 with a temporary API container, then removed that container. WP-045 validated the updated inactive JSON (629 tests). The imported n8n copy still uses the old URL.

## Safe next stage
Before changing the local n8n runtime, verify CLI behavior when importing a workflow ID that already exists, whether the imported copy would remain inactive, and whether changes to a prior imported workflow could be overwritten. Record rollback and collision handling. Stop if semantics are uncertain.

Subsequent changes need explicit approval: update only the inactive workflow, create its named Data Table, configure the two private local credentials, and temporarily start the private static FastAPI container for an authenticated synthetic connectivity check. Separate authorization remains necessary to trigger the webhook or execute/activate any workflow.

## Hard exclusions
No external sends, production/customer data, migrations, real database, Ollama, paid API, VPS, host port publication, existing Docker network changes or unrelated container changes. No credential values in Git/reports. Never treat workflow import or static tests as proof of end-to-end execution. The n8n static-data rate guard is not a concurrency security boundary.

## State
No local action is requested by this document. Await explicit user authorization and issue an exact SHA-bound local handoff. STOP.
