# n8n Local Capability Report — WP-038 Preflight

**Timestamp (UTC):** 2026-10-14T17:33:00Z
**Purpose:** Read-only local inspection of the n8n installation on Ubuntu, to validate version and capabilities before any workflow implementation.

---

## Container Summary

| Field | Value |
|-------|-------|
| Container name | `n8n` |
| Image | `docker.n8n.io/n8nio/n8n:2.40.7` |
| State | Up 8 hours |
| Published ports | `5678/tcp` (no host port mapping; exposed only on Docker network) |

---

## n8n Version

| Field | Value |
|-------|-------|
| CLI version (`n8n --version`) | `2.40.7` |

---

## Health Check

| Endpoint | Method | Status |
|----------|--------|--------|
| `http://127.0.0.1:5678/healthz` | GET (via Node.js `fetch` inside container) | **200 OK** |

**Note:** `curl` is not available in the image; health was verified using `node -e "fetch(...)"`.

---

## Docker Networks

| Network name |
|--------------|
| `n8n_default` |

---

## Capabilities Inventory

Each candidate node was verified by locating its compiled `.node.js` file inside the `n8n-nodes-base` package within the container.

| Capability | Available | Evidence (node/package path inside container) |
|------------|-----------|----------------------------------------------|
| Webhook | ✅ Yes | `n8n-nodes-base/dist/nodes/Webhook/Webhook.node.js` |
| Respond to Webhook | ✅ Yes | `n8n-nodes-base/dist/nodes/RespondToWebhook/RespondToWebhook.node.js` |
| HTTP Request | ✅ Yes | `n8n-nodes-base/dist/nodes/HttpRequest/HttpRequest.node.js` (V1, V2, V3 variants) |
| Code | ✅ Yes | `n8n-nodes-base/dist/nodes/Code/Code.node.js` (JS + Python support) |
| Wait | ✅ Yes | `n8n-nodes-base/dist/nodes/Wait/Wait.node.js` |
| Remove Duplicates | ✅ Yes | `n8n-nodes-base/dist/nodes/Transform/RemoveDuplicates/RemoveDuplicates.node.js` |
| Data Table | ✅ Yes | `n8n-nodes-base/dist/nodes/DataTable/` (directory present) |
| Execute Workflow | ✅ Yes | `n8n-nodes-base/dist/nodes/ExecuteWorkflow/ExecuteWorkflow/ExecuteWorkflow.node.js` |

**All 8 candidate capabilities are present in n8n 2.40.7.**

---

## CLI Import Syntax (Summary)

Command: `n8n import:workflow`

| Flag | Description |
|------|-------------|
| `-i, --input <value>` | Input file name or directory (if `--separate`) |
| `--separate` | Import all `*.json` files from a directory |
| `--userId <value>` | Assign imported workflows to a specific user |
| `--projectId <value>` | Assign imported workflows to a specific project |
| `--activeState` | Respect JSON `active` field. Default `false` deactivates all imports. `fromJson` preserves per-workflow state. |
| `-h, --help` | Show CLI help |

**Key behavior:** By default (`--activeState=false`), all imported workflows are **deactivated**. Use `--activeState=fromJson` to preserve the `active` field from the JSON.

---

## Limitations & Observations

1. **No host port mapping:** The container exposes `5678/tcp` but does not publish it on the host. External access requires Docker network connectivity or a reverse proxy.
2. **No curl in container:** Health checks must use Node.js `fetch` or similar; `curl` is not installed in the image.
3. **Data Store (native n8n persistence):** The search for `DataStore` returned `N8nTrainingCustomerDatastore`, which is a training/example node, not the native n8n Data Store feature. The native Data Store capability (introduced in n8n 1.x for persistent key-value storage) should be verified via the n8n API or UI in a follow-up step.
4. **Single Docker network:** The container is attached only to `n8n_default`. Cross-service communication requires services on the same network or explicit network linking.
5. **Read-only scope:** This report contains no credentials, workflow data, environment variables, or sensitive configuration.

---

## Conclusion

**PASS** — n8n 2.40.7 is running, healthy, and contains all 8 candidate nodes required for the commercial intake workflow. No blocking issues found. The installation is ready for workflow design in the next work package.
