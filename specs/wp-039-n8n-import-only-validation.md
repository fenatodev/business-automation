# WP-039 — Import-only validation of n8n commercial intake workflow

Status: local validation only.

Base workflow:
`ops/n8n/workflows/client0-commercial-intake-review.json`

Objective: prove that n8n 2.40.7 accepts the GitHub-authored workflow JSON
without activation or runtime effects.

## Allowed local effects

- create a fresh temporary clone of the exact repository revision;
- copy only the workflow JSON into `/tmp` inside the existing `n8n` container;
- run `n8n import:workflow` with default inactive behavior;
- remove only the copied temporary file;
- create a short report in this branch and push it.

The imported workflow may be created in n8n **inactive only**. No node may execute.

## Forbidden

- no `--activeState=fromJson`;
- no activation/publish;
- no credentials creation or modification;
- no Data Table creation;
- no webhook call;
- no FastAPI call;
- no Ollama call;
- no Docker restart/network/env/compose change;
- no export of existing workflows or credentials;
- no database inspection;
- no Oracle changes;
- no edits to the workflow JSON during local validation.

## Exact branch

Create:
`wp/039-n8n-import-only-validation`

from exact main commit specified by the chat handoff.

## Procedure

1. Clone into a NEW temporary directory:
   `https://github.com/fenatodev/business-automation.git`.
2. Verify HEAD equals the handoff SHA.
3. Verify workflow JSON has `"active": false`.
4. Copy it:
   `docker cp ops/n8n/workflows/client0-commercial-intake-review.json n8n:/tmp/client0-commercial-intake-review.json`
5. Import without activeState override:
   `docker exec n8n n8n import:workflow --input=/tmp/client0-commercial-intake-review.json`
6. Record only sanitized result: exit code and concise success/error.
7. Remove only:
   `docker exec n8n rm -f /tmp/client0-commercial-intake-review.json`
8. Do not execute or activate the imported workflow.

If import reports unresolved credential/table references but still succeeds,
record that as expected pending configuration. If import rejects schema/node
parameters, STOP and report the exact sanitized validation error; do not edit
locally.

## Deliverable

Create only:
`docs/operations/n8n-import-validation-report.md`

Contents:
- UTC timestamp;
- n8n version;
- exact repo commit;
- import PASS/FAIL;
- exit code;
- whether CLI states imported workflow is inactive, if reported;
- warnings about unresolved credential/table refs;
- blocker, if any.

Then:
`git diff --check`
commit + push branch, no PR merge.

STOP.
