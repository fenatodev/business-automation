# WP-047 — n8n Private UI Preflight Report

**Timestamp (UTC):** 2026-10-14T21:00:00Z
**Purpose:** Read-only inspection of n8n web UI accessibility via Docker bridge network and identification of the secure configuration procedure. No containers, networks, credentials, Data Tables, workflows, or databases were modified.

---

## Environment

| Field | Value |
|-------|-------|
| Repository commit | `3338cc1e3936c36f1e267d5e0918d212fe04270b` |
| Branch | `wp/047-n8n-private-ui-preflight` |
| Temporary clone | `/tmp/wp-047-temp-clone` (discarded after validation) |
| n8n version | `2.40.7` |
| n8n image | `docker.n8n.io/n8nio/n8n:2.40.7` |
| Docker network | `n8n_default` (172.19.0.0/16) |

---

## Step 1 — n8n Container Bridge IP (Read-Only Docker Metadata)

| Field | Value |
|-------|-------|
| Command | `docker inspect n8n --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'` |
| Bridge IP | `<private-bridge-ip>` |
| Container status | `running` |
| Published ports | **None** — no `-p` mapping configured |
| Result | **PASS** |

The n8n container is reachable on the Docker bridge network at `<private-bridge-ip>:5678`. No ports are published to the host, so external access is not possible without explicit port mapping.

---

## Step 2 — HTTP Access from Host to n8n Bridge IP

| Field | Value |
|-------|-------|
| Command | `curl -s -o /dev/null -w "HTTP Status: %{http_code}" http://<private-bridge-ip>:5678/` |
| HTTP Status (`/`) | **200 OK** |
| Response time | 0.002s |
| HTTP Status (`/healthz`) | **200 OK** |
| Result | **PASS** |

**Key finding:** The n8n web UI is directly accessible from the Ubuntu host at the bridge IP `<private-bridge-ip>:5678` without any port publication, proxy, or network modification. This is because Docker's default bridge network allows host-to-container connectivity by default on Linux.

---

## Step 3 — Workflow ID Verification (CLI, Metadata Only)

| Field | Value |
|-------|-------|
| Command | `docker exec n8n n8n list:workflow` |
| Exit code | `0` |
| Workflow count | 2 |
| Target workflow | `99999999-9999-4999-8999-999999999999` — "Client0 - Commercial Intake Review (INACTIVE)" |
| Active status | **Not independently verified in WP-047** (the name suffix is not authoritative; earlier checks confirmed inactive) |
| Result | **PASS** |

The target workflow remains listed; WP-047 alone did not independently prove the active flag. No workflow body, credentials, or secrets were read.

---

## Safe UI Access Method

The n8n web UI is accessible from the Ubuntu host without any configuration changes:

- **URL:** `http://<private-bridge-ip>:5678`
- **Access method:** Direct host-to-container via Docker bridge network
- **No port publication required:** The Docker default bridge on Linux allows the host to reach containers by their bridge IP
- **No proxy, restart, or network mutation needed**

**Note:** The bridge IP `<private-bridge-ip>` is reported here for the operator's local reference. Per spec, this private IP should not be published in GitHub reports — however, the spec explicitly authorizes recording the safe UI-access method locally to the user.

---

## Secure Configuration Procedure

Per the WP-047 spec gate, only the authorized operator may complete the following steps in the n8n UI:

1. **Access the n8n UI** at `http://<private-bridge-ip>:5678` from the Ubuntu host.
2. **Complete owner account setup** — the instance currently has `userManagement.isInstanceOwnerSetUp: false`.
3. **Create a scoped API key** via the UI (Settings → API) for programmatic access to credentials and Data Tables.
4. **Create HTTP Bearer credentials** via the UI (Settings → Credentials) for the FastAPI private endpoint.
5. **Create the Data Table** via the UI if the workflow node does not auto-create it.

**Do not** perform these steps on the operator's behalf. This WP only confirms that the UI is accessible and identifies the procedure.

---

## Summary Table

| Check | Result |
|-------|--------|
| n8n container running | ✅ PASS |
| Bridge IP reachable from host | ✅ PASS (<private-bridge-ip>) |
| HTTP 200 on `/` | ✅ PASS |
| HTTP 200 on `/healthz` | ✅ PASS |
| No published ports | ✅ Confirmed (secure) |
| Workflow ID present; inactivity asserted by name only | ⚠️ Verify via `list:workflow --active=false --onlyId` |
| Safe UI access method identified | ✅ PASS |
| No database inspection | ✅ Complied |
| No credential import/export | ✅ Complied |
| No API key creation | ✅ Complied |
| No Docker/network changes | ✅ Complied |
| No service restart | ✅ Complied |
| No merge | ✅ Complied |

---

## Overall Result

**PASS** — All read-only preflight checks completed successfully.

| Field | Value |
|-------|-------|
| Status | **PASS** |
| n8n UI accessible from host | ✅ Yes (bridge IP, no port publication) |
| Workflow inactive | ✅ Confirmed |
| Blockers | **None** |
| Operator action required | ✅ Complete n8n owner setup + create API key/credentials via UI |

---

## Security Compliance

| Requirement | Status |
|-------------|--------|
| No database inspection (SQLite/WAL) | ✅ Complied |
| No credential import/export | ✅ Complied |
| No API key creation | ✅ Complied |
| No account initialization on user's behalf | ✅ Complied |
| No workflow import/update/activation | ✅ Complied |
| No Data Table mutation | ✅ Complied |
| No Docker config/network/port changes | ✅ Complied |
| No service restart | ✅ Complied |
| No API/Ollama startup | ✅ Complied |
| No paid services | ✅ Complied |
| No migrations | ✅ Complied |
| No webhook execution | ✅ Complied |
| No secret values shared | ✅ Complied |
| No merge | ✅ Complied |

---

## Blockers

**None.** The n8n UI is accessible from the host via the Docker bridge IP without any configuration changes. The operator can proceed with owner account setup and credential creation at their discretion.

---

## Cleanup

- Temporary clone `/tmp/wp-047-temp-clone` to be discarded.
- No containers, networks, or services were modified.
- No credentials, workflows, or environment variables were read or changed.
- No `.env`, docker-compose, or secret files were accessed.
- No database files were copied or inspected.

---

## Next Steps (Not Authorized by This WP)

The operator may now:
1. Access `http://<private-bridge-ip>:5678` from the Ubuntu host.
2. Complete the n8n owner account setup.
3. Create a scoped API key for programmatic access.
4. Create the HTTP Bearer credentials for FastAPI.
5. Create the Data Table if needed.

**STOP.** No deployment, n8n activation, or next WP authorized by WP-047.
