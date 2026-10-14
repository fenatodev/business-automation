# n8n Private Connectivity Report — WP-041 Preflight

**Timestamp (UTC):** 2026-10-14T18:20:00Z
**Purpose:** Read-only inspection of existing connectivity between n8n and private FastAPI endpoint on Ubuntu. No deployment, activation, or configuration changes.

---

## Environment

| Field | Value |
|-------|-------|
| Base commit | `ad6af455e5a8ea96282b3434a5f0a31783382f68` |
| n8n version | `2.40.7` |
| n8n image | `docker.n8n.io/n8nio/n8n:2.40.7` |
| n8n health | **200 OK** via `http://127.0.0.1:5678/healthz` (inside container) |

---

## Docker Containers Summary

Only containers relevant to n8n and API connectivity are listed. No secret values exposed.

| Container | Status | Network | Published Ports |
|-----------|--------|---------|-----------------|
| `n8n` | Up 9 hours | `n8n_default` | `5678/tcp` (no host mapping) |
| `n8n-runners-1` | Up 9 hours | `n8n_default` | `5680/tcp` |
| `n8n-sandbox-runner-1-1` | Up 9 hours | `n8n_default` | `2375-2376/tcp, 8080/tcp` |
| `n8n-sandbox-api-1` | Up 9 hours (healthy) | `n8n_default` | `8080/tcp, 9090/tcp` |
| `business-automation-dev-postgres-1` | Up 9 hours (healthy) | `business-automation-dev_default` | `127.0.0.1:55432->5432/tcp` |
| `searxng` | Up 9 hours | `searxng_default` | `127.0.0.1:8888->8080/tcp` |

**Observation:** No FastAPI container is running. No container named `fastapi`, `uvicorn`, `api`, or `business-automation-api` exists.

---

## n8n Docker Networks

| Network name |
|--------------|
| `n8n_default` |

The n8n container is attached exclusively to `n8n_default`. The PostgreSQL container (`business-automation-dev-postgres-1`) is on a different network (`business-automation-dev_default`). No shared network exists between n8n and any potential FastAPI service.

---

## FastAPI Service Status

### Host Listener Check (`ss -ltn`)

| Check | Result |
|-------|--------|
| Port `8000` listening on host | **NOT FOUND** |
| Port `8000` listening on any interface | **NOT FOUND** |
| Any uvicorn/FastAPI process | **NOT FOUND** |

**The FastAPI service is not running on the host.** No process is bound to port 8000 or any other port that would correspond to the private API endpoint.

### Relevant Host Listeners

| Local Address:Port | Likely Service |
|--------------------|----------------|
| `127.0.0.1:55432` | PostgreSQL (mapped to container) |
| `127.0.0.1:8888` | SearXNG (mapped to container) |
| `127.0.0.1:631` | CUPS |
| `127.0.0.1:53` / `127.0.0.54:53` | DNS resolver |
| `*:3389` | RDP |

---

## DNS Resolution from n8n Container

### `host.docker.internal`

| Method | Result |
|--------|--------|
| `getent hosts host.docker.internal` | **NOT AVAILABLE** — `getent` not installed in n8n image |
| Node.js `dns.lookup('host.docker.internal')` | **DNS RESOLUTION FAILED** — error returned, no address |

**`host.docker.internal` does not resolve from inside the n8n container.** This hostname is the target used by the workflow's HTTP Request node to reach the FastAPI endpoint.

---

## Workflow Target URL Analysis

File inspected (read-only): `ops/n8n/workflows/client0-commercial-intake-review.json`

| Field | Value |
|-------|-------|
| HTTP Request node name | `Evaluate Private Intake API` |
| Configured URL | `http://host.docker.internal:8000/internal/commercial-intake/evaluate` |
| Authentication type | `genericCredentialType` |
| Method | Configured (not inspected in detail) |

**Mismatch identified:** The workflow targets `host.docker.internal:8000`, but:
1. `host.docker.internal` does not resolve from the n8n container.
2. No service listens on port 8000 on the host.
3. Even if DNS resolved, the endpoint would be unreachable.

---

## Connectivity Feasibility Assessment

| Check | Status | Notes |
|-------|--------|-------|
| n8n container running | ✅ Yes | Healthy, version 2.40.7 |
| FastAPI running | ❌ No | No listener on port 8000, no container found |
| `host.docker.internal` DNS | ❌ No | DNS lookup fails from inside n8n |
| Shared Docker network | ❌ No | n8n on `n8n_default`, no API container exists |
| Network path n8n → FastAPI | ❌ Unreachable | Both DNS and service are absent |

---

## Unknowns

1. **FastAPI deployment method unknown:** It is unclear whether the FastAPI service is intended to run as a Docker container, a host process, or via another mechanism. The `AGENTS.md` references Docker Compose, but no API service is currently active.
2. **`host.docker.internal` support:** The Docker runtime on this Ubuntu host does not appear to provide the `host.docker.internal` DNS alias to containers on user-defined networks. This is a known limitation on Linux Docker (available by default on Docker Desktop for Mac/Windows).
3. **Credential configuration:** The workflow uses `genericCredentialType` authentication. No credentials have been created in n8n for this endpoint.

---

## Recommended Smallest Future Change

To enable n8n → FastAPI connectivity, the following minimal changes would be required in a future WP:

1. **Start the FastAPI service** on the host or as a container (port 8000).
2. **Ensure DNS reachability:** Either:
   - Run FastAPI as a container on the `n8n_default` network and use the container name as hostname (e.g., `http://fastapi:8000/...`); or
   - Add `--add-host=host.docker.internal:host-gateway` to the n8n container run/create options; or
   - Use a custom Docker network shared by both n8n and the API container.
3. **Update the workflow URL** if the hostname changes from `host.docker.internal` to a Docker-internal name.
4. **Create the generic credentials** in n8n for the API authentication.

---

## Conclusion

**PASS** — The read-only inspection completed successfully. All permitted checks were executed without modifying any service, configuration, or data.

**Connectivity status: NOT VERIFIED** — The n8n container cannot reach the FastAPI endpoint because:
- The FastAPI service is not running.
- `host.docker.internal` does not resolve from the n8n container.
- No shared network path exists.

**Blocker for runtime:** FastAPI must be started and network connectivity between n8n and the API must be established before the workflow can execute the HTTP Request node. This is a configuration dependency, not a defect in the workflow JSON or n8n installation.

---

## Cleanup

- No containers, networks, or services were modified.
- No credentials, workflows, or environment variables were read or changed.
- No `.env`, docker-compose, or secret files were accessed.
- No workflow was activated or executed.
- No temporary files were created on the host or in any container.
