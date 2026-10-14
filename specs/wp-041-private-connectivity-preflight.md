# WP-041 — Read-only n8n → private API connectivity preflight

Status: **inspection only; no deployment, activation, or configuration**.

## Goal
Resolve whether the existing n8n 2.40.7 container can reach the existing private FastAPI endpoint, and whether that endpoint is actually running. Produce evidence to select a secure local connectivity method. This WP does NOT authorize starting any service or modifying any runtime configuration.

## Preconditions
- Clone a fresh temporary checkout of the exact `main` commit provided in the handoff.
- Read `AGENTS.md` and this entire spec.
- Create branch `wp/041-private-connectivity-preflight`.
- Only inspect the existing containers/network listeners; never read environment values or secrets.
- A prior WP-040 import succeeded but the workflow is inactive. Do not activate or execute it.

## Permitted checks (read-only)
1. `docker ps --format '{{.Names}} {{.Status}} {{.Networks}} {{.Ports}}'` (record only relevant n8n/API services, with no secret values).
2. `docker inspect n8n --format '{{json .NetworkSettings.Networks}}'` (summarize network names only; do not publish IPs).
3. `getent hosts host.docker.internal` from inside n8n **only if executable is present**. If unavailable, record that fact; do not install tools. A missing DNS entry must not trigger changes.
4. Check whether a FastAPI service already has a bound local listener using `ss -ltn` on host; report existence and bound interface only (no access tokens).
5. If an n8n-bundled read-only HTTP client is available, request ONLY a harmless public/health endpoint, **not** `/internal/commercial-intake/evaluate`. If no verified safe URL/client exists, skip network request. Do not use credentials or invoke a commercial endpoint.
6. Inspect `ops/n8n/workflows/client0-commercial-intake-review.json` from the temporary checkout to compare configured target URL to observed service reachability. Do not edit it.

## Forbidden
- No writing to n8n database or inspecting it.
- No reading/editing credentials, workflow records, `.env`, docker-compose, secret files, logs containing payloads, or client data.
- No service start, restart, image pull, install, network/port change, import or workflow run.
- No API call requiring auth, no bearer token, no POST, no webhook, no Ollama.
- No public exposure, SSH tunnel, host-gateway configuration or external API.
- No change to operational checkout, `main` or existing workflow.
- No merge or other WP.

## Deliverable
Create only `docs/operations/n8n-private-connectivity-report.md` with UTC time, base SHA, n8n health, whether FastAPI exists/runs, whether `host.docker.internal` resolves from n8n (or not testable), listener binding, feasibility/unknowns, recommended smallest **future** change and explicit PASS/FAIL for inspection (not connectivity if unverified).

Run `git diff --check`, commit, push branch and STOP.
