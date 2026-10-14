# WP-044 — Private API build and isolated connectivity proof (approval gated)

Status: **prepared, NOT authorized for execution**.

## Evidence
- WP-040: n8n workflow imported inactive successfully.
- WP-041: no FastAPI running, `host.docker.internal` DNS absent.
- WP-042: optional Dockerfile/Compose parsed; guardrail tests PASS.
- WP-043 correction: full test suite 629 PASS; private ASGI only includes authenticated intake endpoint.
- No published ports or external send nodes.

## Authorization gate
**Do not run this WP until the user explicitly authorizes building/starting a private local container.** This gate is separate from permission to update GitHub. No paid API, VPS, cloud, WhatsApp or outbound send is authorized.

## Stage 1 — Local preflight (no mutation)
- Exact fresh temporary checkout pinned to handoff SHA.
- Verify n8n_default network still exists; verify no `ba-private-api` service/container collision.
- Check Dockerfile/Compose are unchanged and `active=false` in workflow. Validate external network only; do not inspect credentials.
- Check local build disk capacity and note any likely downloads, without pulling images.

## Stage 2 — Only if explicitly approved
- Build only `ba-private-api` image via separate optional Compose, without starting other Compose services or touching n8n.
- Generate a local-only non-production `BA_PRIVATE_ENV_FILE` with dummy disconnected `DATABASE_URL` and a fresh synthetic **operator** identity; no secrets printed, committed, or pasted into logs.
- Confirm the application starts in static mode with restricted ASGI entrypoint and no database access/migration. **Do not expose host ports**.
- Verify private DNS and a harmless HTTP 401 response to unauthenticated synthetic POST from an existing authorized private-network probe; never send customer data. Do not call live n8n workflow.
- Stop and remove only containers created by this WP if the test ends or fails. Do not delete images or volumes and do not disconnect other containers.
- Produce a sanitized evidence report (HTTP status, DNS result, no actual credentials or network addresses).

## STOP conditions
Missing authority, unknown network state, failed image build, auth misconfiguration, any unexpected inbound/outbound traffic, real DB dependency, any request to expose host port or activate workflow. STOP, do not attempt a workaround.

## Deliverable
Commit sanitized report to a dedicated branch and push. No merge. No workflow/credentials/Data Table changes. No activation; no outbound messages. 
