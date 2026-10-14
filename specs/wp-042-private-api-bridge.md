# WP-042 — Private n8n-to-FastAPI bridge (offline implementation and local dry-run)

Status: **design and non-mutating validation only**. No runtime activation authorized.

## Verified inputs
- WP-040: n8n 2.40.7 successfully imported the review workflow as inactive.
- WP-041: n8n is healthy on `n8n_default`; FastAPI is **not running**; `host.docker.internal` does **not** resolve.
- Repository `docker-compose.yml` currently defines only PostgreSQL. The application needs `DATABASE_URL` to import settings even for its no-DB intake endpoint.
- The endpoint requires a private operator Bearer identity. It uses static generation by default and forbids sends.

## Decision and boundaries
Prefer a **separate private API container attached to the existing n8n network** over changing n8n DNS, exposing API on the host, or publishing ports. This is a proposed local pilot configuration, not yet approved for activation. No SaaS, VPS, paid LLM or cloud.
- Do **not** add any `ports:` mapping to the API container.
- Attach API only to the pre-existing `n8n_default` external Docker network, with an unambiguous private network alias. Keep PostgreSQL separate unless real DB access is explicitly needed.
- Pin dependencies via `uv.lock` and avoid installing development dependencies for the runnable image.
- Keep operator credentials, identity hashes and `DATABASE_URL` in a **local-only** configuration, outside Git. No real DB reads/writes during pilot tests.
- Default `BA_INTAKE_GENERATOR=static`. Do not start Ollama. Disable debug and avoid logging request bodies.
- Keep n8n workflow `active=false`. Do not bind credentials, create Data Tables, execute the workflow, or change its already imported copy during this WP.
- Preserve existing `docker-compose.yml` for PostgreSQL. Provide separate optional artifacts only.

## Phase A — GitHub-first engineering (no local runtime)
Prepare, in a separate branch and PR, the smallest optional files required for a private API container and a local static-mode smoke check. Scope:
1. Minimal pinned container image build (Python 3.12) from the existing app and lockfile; no optional database migration or startup side effects. Explicit command starts Uvicorn on port 8000 inside the private network **only after a distinct authorization gate**.
2. A separate opt-in Compose file referencing `n8n_default` as an **existing external network**, no host port mapping, with a unique service/network alias. Must not create/modify n8n containers.
3. README/runbook documenting local-only operator identity provisioning, non-sensitive reachability checks, cleanup, failure modes, and exact non-activation gates.
4. Static tests ensuring: no published ports, no `network_mode: host`, no `privileged`, no `docker.sock`, no hard-coded tokens, inactive n8n workflow, default static generator, no migrations, no automatic n8n import. Include an explicit note that tests cannot prove live network reachability.

**Security review mandatory** before applying Phase B. The full API exposes additional authenticated routes within its container network; describe blast radius and why a dedicated minimal-intake-only ASGI app would be safer for a later production milestone. For the pilot, do not call it production secure.

## Phase B — Ubuntu dry-run (Junie only after Phase A merged)
- Fresh temporary clone at an exact handoff SHA.
- Inspect only metadata of the existing `n8n_default` network (no secrets).
- Run syntax/parse validations for the new optional Compose and Dockerfile, and lint/tests using synthetic input and no real DB.
- **Do not** run `docker compose up`, `build`, `run`, `exec` against a live service, create any container, install a model, read `.env`, or start the API. No configuration or network mutation.
- Report `PASS/FAIL`, command exit codes, and blockers in `docs/operations/wp-042-private-bridge-validation-report.md` via a WP branch. No merge.

## Explicit approval gate after dry-run
Only after review may a separate WP request approval to create/start the private API container, bind local credentials, test API reachability using synthetic data, or alter n8n configuration. None of these effects are authorized by WP-042. Never enable external sending or incur paid API/VM costs without separate advance authorization.

## STOP
No deployment, n8n activation, commercial messaging, credential changes, DB migrations, public endpoint or next WP.
