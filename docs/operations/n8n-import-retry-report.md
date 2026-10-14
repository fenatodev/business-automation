# n8n Import Retry Report — WP-040

**Timestamp (UTC):** 2026-10-14T18:05:00Z
**Purpose:** Re-run import-only validation against the corrected workflow JSON and prove that n8n 2.40.7 accepts it without activation or execution.

---

## Environment

| Field | Value |
|-------|-------|
| n8n version | `2.40.7` |
| n8n image | `docker.n8nio/n8n:2.40.7` |
| Repository commit | `e2d33c1c896c3d066066ee8bf64176ab2db003b7` |
| Workflow file | `ops/n8n/workflows/client0-commercial-intake-review.json` |

---

## Workflow JSON Pre-Check

| Field | Value |
|-------|-------|
| Top-level `"id"` field | **Present** — `99999999-9999-4999-8999-999999999999` |
| `"active"` field | `false` |
| Workflow name | `Client0 - Commercial Intake Review (INACTIVE)` |
| Nodes | 7 |
| Connections | 6 |

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

All 7 nodes have valid UUID-style IDs. The top-level `"id"` field is present (fix from WP-039 blocker). The `"active": false` field is correctly set.

---

## Import Result

**Result: PASS**

| Field | Value |
|-------|-------|
| Command | `n8n import:workflow --input=/tmp/client0-commercial-intake-review.json` |
| Exit code | `0` |
| CLI output | `Importing 1 workflows... Successfully imported 1 workflow.` |
| Workflow imported | Yes (inactive) |
| Workflow activated | No |

---

## Comparison with WP-039

| Field | WP-039 (FAIL) | WP-040 (PASS) |
|-------|---------------|---------------|
| Commit | `216b405` | `e2d33c1` |
| Top-level `"id"` | **Missing** | `99999999-9999-4999-8999-999999999999` |
| Exit code | `1` | `0` |
| Error | `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id` | None |

The sole blocker from WP-039 — missing top-level `"id"` field — has been resolved in commit `e2d33c1`.

---

## Warnings

1. **Unresolved Data Table reference (expected):** The workflow contains a `n8n-nodes-base.dataTable` node (`Queue for Human Review`) that references a Data Table not yet created in n8n. This is an expected configuration dependency that will be resolved when the Data Table is provisioned. The import CLI accepted the workflow without error, but runtime execution would fail until the Data Table exists.
2. **Unresolved credential references (expected):** The `Evaluate Private Intake API` node (`n8n-nodes-base.httpRequest`) may reference credentials not yet configured in n8n. This is an expected pending configuration item.

---

## Cleanup

- Temporary file `/tmp/client0-commercial-intake-review.json` removed from n8n container.
- Workflow imported in **inactive** state only. No nodes executed.
- No credentials, Data Tables, or environment changes were made.
- No existing n8n data was read or modified.

---

## Conclusion

**PASS** — Import retry validation succeeded. The corrected workflow JSON (with top-level `"id"` field) is accepted by n8n 2.40.7 without activation. The WP-039 blocker has been fully resolved. No blocking issues remain for import. Pending configuration items (Data Table, credentials) are expected and will be addressed in future work packages.
