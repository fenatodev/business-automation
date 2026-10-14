# WP-042 — Private API bridge: GitHub-authored inactive artifacts

**Status:** static artifacts only. No container has been built or started.

- Optional Dockerfile and Compose: `ops/private-api/`.
- Service `ba-private-api` will join the **existing** external `n8n_default` network when started by a separately authorized operation. This does not publish a host port.
- Name/URL **proposed** for a future n8n workflow revision: `http://ba-intake-private:8000/internal/commercial-intake/evaluate`.
- Keep the already imported workflow inactive; its current `host.docker.internal` URL remains unchanged until connectivity is proven and a new JSON import/rebinding step is authorized.
- The running API would include **other authenticated application routes**. They are reachable by peers on that Docker network. For production, minimize ASGI surface to the intake endpoint and audit tenant identity and network policy separately.
- The API module requires `DATABASE_URL` at import time even though this endpoint performs no database operations. Use a nonproduction, non-real database URL in the private local env file for a synthetic-only test; do **not** point this container to any existing production/development database without separate authorization.
- `BA_ACCESS_IDENTITIES_JSON` requires a locally configured operator identity. Never commit token hashes or raw token values. `BA_INTAKE_GENERATOR=static` is forced by Compose.
- `BA_PRIVATE_ENV_FILE` must resolve to a preexisting local secret file outside the repository; no file is provided or read by GitHub.
- Build requires access to fetch base image/Python packages. It is **not part of local dry-run** and may have network/bandwidth costs; confirm before building.
- `docker compose -f ops/private-api/compose.private.yml config --no-interpolate` can be used for inspection; do not render or copy environment/secret values into reports.
- No n8n credential or Data Table was created, no message was sent, no model was started, no ports were published.

Next: only static/parse validation on an isolated temporary clone (WP-042 Phase B). After PASS, a distinct approval gate is mandatory before Docker build/start or altering n8n.
