# WP-046 — n8n Private Integration Report

**Timestamp (UTC):** 2026-10-14T20:00:00Z
**Purpose:** Configure the private integration between FastAPI and n8n for synthetic testing only. This report documents the diagnostic phase — which operations succeeded, which failed, and the current state.

---

## Environment

| Field | Value |
|-------|-------|
| Base commit | `d7e400aaa985363ac87a6fe2e6280cb7ee232195` |
| Branch | `wp/046-n8n-private-integration` |
| n8n version | `2.40.7` |
| n8n image | `docker.n8n.io/n8nio/n8n:2.40.7` |
| Docker network | `n8n_default` (172.19.0.0/16) |
| FastAPI image | `ba-private-api:latest` (375 MB, from WP-044) |
| Temporary clone | `/tmp/wp-046-temp-clone` |

---

## Operations Summary

| # | Operation | Status | Details |
|---|-----------|--------|---------|
| 1 | Preflight: verify environment | **PASS** | n8n healthy, network exists, image available |
| 2 | Import workflow JSON | **PASS** | Exit 0, "Successfully imported 1 workflow" |
| 3 | Verify workflow inactive | **PASS** | `active=false`, 7 nodes, URL `ba-intake-private:8000` |
| 4 | Collision test: re-import same ID | **PASS** | Exit 0, workflow remains inactive after overwrite |
| 5 | Create Data Table | **NOT STARTED** | Blocked by API auth (see below) |
| 6 | Configure credentials | **NOT STARTED** | Blocked by API auth (see below) |
| 7 | Start temporary FastAPI | **NOT STARTED** | Depends on credentials |
| 8 | Test connectivity | **NOT STARTED** | Depends on FastAPI + credentials |
| 9 | Cleanup | **NOT STARTED** | Nothing to clean yet |

---

## What Succeeded

### Workflow Import (Step 2)

The workflow JSON `ops/n8n/workflows/client0-commercial-intake-review.json` was imported into n8n via `docker cp` + `n8n import:workflow`. The import succeeded with exit code 0.

**Verification via export:**

| Field | Value |
|-------|-------|
| ID | `99999999-9999-4999-8999-999999999999` |
| Name | `Client0 - Commercial Intake Review (INACTIVE)` |
| Active | `False` |
| Nodes | 7 |
| HTTP URL | `http://ba-intake-private:8000/internal/commercial-intake/evaluate` |

### Collision Test (Step 4)

Re-importing the same workflow ID via the CLI succeeded (exit 0) and the workflow remained **inactive**. This confirms that re-importing an existing workflow ID overwrites without activating — safe behavior for future updates.

---

## What Failed

### n8n REST API Authentication

The n8n REST API (`/api/v1/workflows`, `/api/v1/credentials`, `/api/v1/data-tables`) returns **401 Unauthorized** without an API key. The instance has:

- **No user API keys** in `user_api_keys` table (0 rows).
- **No instance owner set up** (`userManagement.isInstanceOwnerSetUp: false`).
- **No way to create an API key** via CLI — the `n8n` CLI has no `api-key:create` command.
- The web UI is not accessible from the host (no published port).

**Impact:** Cannot create Data Tables or Credentials via the REST API without first establishing API authentication. The n8n CLI has no commands for Data Table or Credential management — only `import:workflow`, `export:workflow`, `list:workflow`, and `import:credentials`/`export:credentials`.

### Database WAL Mode

The n8n SQLite database uses WAL (Write-Ahead Logging) mode. Copying only `database.sqlite` yields stale data (0 workflows). A consistent read requires copying all three files: `database.sqlite`, `database.sqlite-shm`, and `database.sqlite-wal`. This was discovered during investigation and does not block operations, but explains why initial DB queries returned empty results.

---

## Current State

| Component | State |
|-----------|-------|
| Workflow | ✅ Imported, inactive, correct URL |
| Data Table | ❌ Not created (0 in DB) |
| Credentials | ❌ Not created (0 in DB) |
| API Key | ❌ Not configured (0 in DB) |
| FastAPI container | ❌ Not started |
| Connectivity test | ❌ Not executed |

---

## Blockers

### BLOCKER: n8n API Authentication

To create Data Tables and Credentials, the n8n REST API requires a valid API key. However:

1. The instance has no API key configured.
2. The n8n CLI provides no command to create API keys.
3. The web UI is not accessible from the host (no published port).
4. Direct DB insertion of an API key requires understanding the JWT signing mechanism used by n8n, which depends on internal modules not accessible from `node -e`.

**Options to resolve:**

1. **Expose n8n UI temporarily** — Add `-p 5678:5678` to the n8n container to access the web UI, create an API key, then remove the port mapping. This requires restarting the container.
2. **Use `import:credentials` CLI** — The n8n CLI supports `import:credentials --input=file.json`. This could create credentials without REST API access, if we can generate the correct JSON format.
3. **Data Table via workflow execution** — If the Data Table node auto-creates the table on first execution, this could be resolved when the workflow runs (but we're not executing workflows per spec).

**Recommendation:** Option 2 is the safest — use `n8n import:credentials` CLI to create the HTTP Bearer credential without exposing ports or restarting containers. For Data Tables, the n8n CLI has no import command; the Data Table may need to be created via the web UI or the node may auto-create it.

---

## Security Compliance

| Requirement | Status |
|-------------|--------|
| Never activate workflows | ✅ Complied — workflow remains inactive |
| No webhook execution | ✅ Complied |
| No messages sent | ✅ Complied |
| No real database access | ✅ Complied — only n8n's own SQLite inspected |
| No migrations | ✅ Complied |
| No public port exposure | ✅ Complied |
| No paid services | ✅ Complied |
| No Ollama | ✅ Complied |
| No other container changes | ✅ Complied |
| No credential values in Git | ✅ Complied |
| No network changes | ✅ Complied |
| No merge | ✅ Complied |

---

## Next Action

The next WP iteration should:

1. Attempt `n8n import:credentials` with a properly formatted HTTP Bearer credential JSON to create the API authentication credential.
2. Investigate whether the Data Table node in the workflow can auto-create the table, or if a separate creation mechanism is needed.
3. Once credentials exist, start the temporary FastAPI container and test authenticated connectivity.

**STOP.** No further changes executed in this round.
