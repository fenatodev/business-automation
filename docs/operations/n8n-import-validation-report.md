# n8n Import Validation Report — WP-039

**Timestamp (UTC):** 2026-10-14T17:47:00Z
**Purpose:** Validate that n8n 2.40.7 imports the GitHub-authored workflow JSON without activation or runtime effects.

---

## Environment

| Field | Value |
|-------|-------|
| n8n version | `2.40.7` |
| n8n image | `docker.n8n.io/n8nio/n8n:2.40.7` |
| Repository commit | `216b405075bb4df7995e8ce31532bd7f916ba0b8` |
| Workflow file | `ops/n8n/workflows/client0-commercial-intake-review.json` |

---

## Workflow JSON Pre-Check

| Field | Value |
|-------|-------|
| File size | 9195 bytes |
| `"active"` field | `false` |
| Workflow name | `Client0 - Commercial Intake Review (INACTIVE)` |
| Nodes | 7 |
| Connections | 6 |
| Top-level `"id"` field | **MISSING** |

### Nodes Inventory

| # | Node ID | Type | Name |
|---|---------|------|------|
| 0 | `11111111-1111-4111-8111-111111111111` | `n8n-nodes-base.webhook` | Inbound Webhook |
| 1 | `22222222-2222-4222-8222-222222222222` | `n8n-nodes-base.code` | Normalize Safe Input |
| 2 | `33333333-3333-4333-8333-333333333333` | `n8n-nodes-base.removeDuplicates` | Persistent Event Dedupe |
| 3 | `44444444-4444-4444-8444-444444444444` | `n8n-nodes-base.code` | Coarse Rate Guard |
| 4 | `55555555-5555-4555-8555-555555555555` | `n8n-nodes-base.httpRequest` | Evaluate Private Intake API |
| 5 | `66666666-6666-4666-8666-666666666666` | `n8n-nodes-base.code` | Build Review Queue Row |
| 6 | `77777777-7777-4777-8777-777777777777` | `n8n-nodes-base.dataTable` | Queue for Human Review |

All 7 nodes have valid UUID-style IDs. The `"active": false` field is correctly set.

---

## Import Result

**Result: FAIL**

| Field | Value |
|-------|-------|
| Command | `n8n import:workflow --input=/tmp/client0-commercial-intake-review.json` |
| Exit code | `1` |
| CLI output | `Importing 1 workflows...` |
| Error | `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id` |
| Workflow imported | No |
| Workflow activated | No |

---

## Root Cause

The workflow JSON file is **missing the top-level `"id"` field**. The n8n database enforces a `NOT NULL` constraint on `workflow_entity.id`, and the import CLI rejects the file before any node-level validation.

This is a **schema defect in the workflow JSON**, not an n8n installation issue. The n8n import tool and database are functioning correctly by rejecting an incomplete workflow definition.

---

## Warnings

1. **Missing `"id"` field:** The workflow JSON must include a top-level `"id"` field (UUID format) for n8n to accept the import. This is a required field in the n8n workflow schema.
2. **Unresolved references (pending):** Even after fixing the `"id"` field, the workflow references a Data Table node (`n8n-nodes-base.dataTable`) that may require a pre-existing Data Table in n8n. This would be a secondary, expected configuration dependency.

---

## Blocker

**BLOCKER:** The workflow JSON file `ops/n8n/workflows/client0-commercial-intake-review.json` must be updated to include a valid top-level `"id"` field before import validation can succeed.

**Recommended fix:** Add `"id": "<uuid>"` to the root of the workflow JSON, where `<uuid>` is a valid UUID v4 string (e.g., `"id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"`).

---

## Cleanup

- Temporary file `/tmp/client0-commercial-intake-review.json` removed from n8n container.
- No workflows were imported or activated.
- No credentials, Data Tables, or environment changes were made.
- No existing n8n data was read or modified.

---

## Conclusion

**FAIL** — Import validation failed due to missing `"id"` field in the workflow JSON. The n8n installation (2.40.7) is healthy and correctly rejects the incomplete schema. The workflow JSON must be fixed in the repository before re-running this validation.
