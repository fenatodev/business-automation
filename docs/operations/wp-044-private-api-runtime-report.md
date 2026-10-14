# WP-044 — Private API Runtime Validation Report

**Timestamp (UTC):** 2026-10-14T18:45:00Z
**Purpose:** Build, start, and validate the private FastAPI container on the n8n Docker network. Approval-gated per spec. No host ports exposed, no real database, no n8n workflow activation.

---

## Environment

| Field | Value |
|-------|-------|
| Base commit | `86d1c2d04a66858e62afaeee81963b3caed2c912` |
| Branch | `wp/044-private-api-runtime-validation` |
| n8n version | `2.40.7` |
| n8n image | `docker.n8n.io/n8nio/n8n:2.40.7` |
| Temporary clone | `/tmp/wp-044-temp-clone` (discarded after validation) |
| Python base image | `python:3.12-slim` |
| uv | `0.9.17` |
| uvicorn | `0.52.4` |
| FastAPI | `0.141.1` |

---

## Stage 1 — Preflight (Read-Only)

| Check | Result |
|-------|--------|
| `n8n_default` network exists | ✅ bridge, local scope |
| `ba-private-api` container collision | ✅ None found |
| Dockerfile/Compose unchanged from HEAD | ✅ No diff |
| Workflow `active` field | ✅ `false` |
| Disk capacity | ✅ 70 GB free on `/` |
| Build disk capacity | ✅ Sufficient (20.6 GB images, 4.3 GB reclaimable) |

---

## Stage 2 — Build

| Field | Value |
|-------|-------|
| Image tag | `ba-private-api:latest` |
| Dockerfile steps | 11/11 |
| Base image | `python:3.12-slim` |
| Packages installed | 51 (via `uv sync --locked --no-dev --no-editable`) |
| Non-root user | `10001:10001` |
| ASGI entrypoint | `app.intake_only:app` |
| Build exit code | `0` |
| Result | **PASS** |

---

## Stage 2 — Synthetic Configuration

A local-only env file was generated in `/tmp` (never committed) with:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `sqlite:///tmp/wp044-synthetic.db` (disconnected, no real DB) |
| `BA_ACCESS_IDENTITIES_JSON` | Single synthetic `operator` identity with fresh SHA-256 token |
| `BA_INTAKE_GENERATOR` | `static` (no Ollama, no network) |

No secrets were printed, committed, or pasted into logs.

---

## Stage 2 — Container Initialization

| Field | Value |
|-------|-------|
| Container name | `ba-private-api` |
| Network | `n8n_default` (shared with n8n) |
| Network alias | `ba-intake-private` |
| Host ports exposed | **None** |
| Container expose | `8000/tcp` (Docker-internal only) |
| Read-only filesystem | ✅ |
| Capabilities | `ALL` dropped |
| No-new-privileges | ✅ |
| User | `10001:10001` |
| Restart policy | `no` |
| Startup logs | `Uvicorn running on http://0.0.0.0:8000` |
| Result | **PASS** |

---

## Stage 2 — DNS Resolution (from n8n container)

| Check | Result |
|-------|--------|
| `ba-intake-private` DNS lookup | ✅ Resolved to `172.19.0.6` |
| TCP connect to `ba-intake-private:8000` | ✅ Connected |

**DNS from n8n to the private API container works correctly on the shared `n8n_default` network.**

---

## Stage 2 — HTTP 401 Test (No Authentication)

| Field | Value |
|-------|-------|
| Source | n8n container (Node.js `http` module) |
| Target | `ba-intake-private:8000/internal/commercial-intake/evaluate` |
| Method | `POST` |
| Auth header | **None** |
| HTTP status | **401** |
| Response body | `{"detail":"Invalid or missing credentials"}` |
| Result | **PASS** — Unauthenticated request correctly rejected |

---

## Stage 2 — Cleanup

| Action | Result |
|--------|--------|
| `docker stop ba-private-api` | ✅ Exit 0 |
| `docker rm ba-private-api` | ✅ Exit 0 |
| Container verified removed | ✅ No container found |
| Image preserved | ✅ `ba-private-api:latest` (375 MB) |
| Host port 8000 listener | ✅ None (confirmed safe) |
| Synthetic env file | ✅ Removed from `/tmp` |

---

## Summary Table

| Check | Exit Code | Result |
|-------|-----------|--------|
| Preflight: n8n_default network | `0` | ✅ PASS |
| Preflight: No container collision | `0` | ✅ PASS |
| Preflight: Files unchanged | `0` | ✅ PASS |
| Build image | `0` | ✅ PASS |
| Container start | `0` | ✅ PASS |
| DNS `ba-intake-private` from n8n | `0` | ✅ PASS |
| TCP connect `ba-intake-private:8000` | Connected | ✅ PASS |
| HTTP 401 without auth | `0` | ✅ PASS (status 401) |
| Container stop | `0` | ✅ PASS |
| Container remove | `0` | ✅ PASS |
| No host ports exposed | Confirmed | ✅ PASS |

---

## Overall Result

**PASS** — All validations completed successfully.

| Field | Value |
|-------|-------|
| Status | **PASS** |
| Build | ✅ Success (11/11 steps) |
| Initialization | ✅ Uvicorn on 0.0.0.0:8000, no host ports |
| DNS | ✅ `ba-intake-private` resolves from n8n container |
| HTTP status | ✅ 401 Unauthorized (no auth) |
| Cleanup | ✅ Container stopped and removed, image preserved |
| Blockers | **None** |

---

## Security Compliance

| Requirement | Status |
|-------------|--------|
| Zero additional cost | ✅ Complied |
| No paid services | ✅ Complied |
| No host port exposure | ✅ Confirmed |
| No real database access | ✅ SQLite disconnected synthetic |
| No migrations | ✅ Complied |
| No real client data | ✅ Complied |
| No n8n workflow changes | ✅ Complied |
| No n8n credentials created | ✅ Complied |
| No Ollama started | ✅ Complied |
| No outbound messages | ✅ Complied |
| No other containers modified | ✅ Complied |
| No main branch changes | ✅ Complied |
| No merge | ✅ Complied |

---

## Blockers

**None.** The private API container builds, starts, and is reachable from n8n via the shared Docker network. Authentication gate works correctly (401 without credentials).

---

## Cleanup

- Temporary clone `/tmp/wp-044-temp-clone` to be discarded.
- Synthetic env file removed from `/tmp`.
- Container `ba-private-api` stopped and removed.
- Image `ba-private-api:latest` preserved (may be removed later if desired).
- No other containers, networks, or services were modified.
- No credentials, workflows, or environment variables were read or changed.
- No `.env`, docker-compose, or secret files were accessed.
- No workflow was activated or executed.

---

## Next Steps (Not Authorized by This WP)

Only after explicit approval may a separate WP:
1. Update the n8n workflow URL from `host.docker.internal:8000` to `ba-intake-private:8000`.
2. Create the generic credentials in n8n for the API Bearer token.
3. Test the full n8n workflow execution against the private API.

**STOP.** No deployment, n8n activation, or next WP authorized by WP-044.
