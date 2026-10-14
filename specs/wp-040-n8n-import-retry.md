# WP-040 — Retry n8n import-only validation after workflow ID fix

Status: local validation only.

## Objective

Re-run the exact import-only validation against the corrected workflow JSON and prove that n8n 2.40.7 accepts it without activation or execution.

Workflow:
`ops/n8n/workflows/client0-commercial-intake-review.json`

## Preconditions

- Use a fresh temporary clone of the exact GitHub revision supplied in the chat handoff.
- Confirm the workflow contains:
  - top-level `id`;
  - `"active": false`.
- Existing n8n container remains unchanged except for the inactive imported workflow if the CLI succeeds.

## Allowed local effects

- fresh temporary clone;
- copy only the workflow JSON into `/tmp` inside container `n8n`;
- run `n8n import:workflow`;
- remove only the temporary copied JSON;
- write the sanitized validation report in the WP branch;
- commit and push that branch.

## Forbidden

- no workflow activation or publish;
- no `--activeState=fromJson`;
- no workflow execution or webhook call;
- no credentials creation/modification;
- no Data Table creation/modification;
- no FastAPI/Ollama call;
- no Docker restart/network/env/compose change;
- no export/read of existing workflows, credentials or database;
- no edits to the workflow JSON locally;
- no merge.

## Branch

Create:
`wp/040-n8n-import-retry`

from the exact main commit supplied in the chat handoff.

## Procedure

1. Clone `https://github.com/fenatodev/business-automation.git` into a new temporary directory and verify HEAD equals the supplied SHA.
2. Verify top-level `id` exists and `active=false`.
3. Copy:
   `docker cp ops/n8n/workflows/client0-commercial-intake-review.json n8n:/tmp/client0-commercial-intake-review.json`
4. Import:
   `docker exec n8n n8n import:workflow --input=/tmp/client0-commercial-intake-review.json`
5. Record real exit code and sanitized CLI result.
6. Remove only:
   `docker exec n8n rm -f /tmp/client0-commercial-intake-review.json`
7. Do not activate or execute the imported workflow.

If import fails, STOP. Do not patch locally. Report the exact sanitized schema/configuration blocker.

## Deliverable

Create only:
`docs/operations/n8n-import-retry-report.md`

Include:
- UTC timestamp;
- n8n version;
- exact repo commit;
- import PASS/FAIL;
- exit code;
- concise sanitized CLI result;
- whether workflow remained inactive, if reported;
- unresolved credential/Data Table warnings;
- blocker, if any.

Then run:
`git diff --check`

Commit + push branch and STOP.
