# WP-043 — Private Intake Validation Report (Offline)

**Timestamp (UTC):** 2026-10-14T18:50:00Z
**Purpose:** Offline validation of restricted private intake ASGI entrypoint. Local synthetic tests only; no Docker or API runtime.

---

## Environment

| Field | Value |
|-------|-------|
| Repository commit | `6cd55243651471ee95f2614b7d396358802b28c7` |
| Temporary clone | `/tmp/wp-043-temp-clone` (discarded after validation) |
| Python | `3.12.3` |
| pytest | via `uv run` |

---

## Test Run 1 — Targeted intake + bridge tests

| Field | Value |
|-------|-------|
| Command | `uv run pytest -q tests/test_private_intake_entrypoint.py tests/test_private_api_bridge_artifacts.py` |
| Exit code | `1` |
| Passed | 5 |
| Failed | 1 |
| Warnings | 1 (StarletteDeprecationWarning — unrelated) |

### Failure Detail

| Test | Error |
|------|-------|
| `test_only_intake_route_registered` | `AttributeError: '_IncludedRouter' object has no attribute 'path'` |

**Root cause:** `app/intake_only.py` uses `app.include_router(commercial_intake_router)`, which adds an `_IncludedRouter` wrapper to `app.routes`. The test iterates `app.routes` directly assuming every item has a `.path` attribute, but `_IncludedRouter` does not expose `.path`. The test code must filter or descend into included routers. This is a defect in the test, not in the ASGI entrypoint.

---

## Test Run 2 — Full test suite

| Field | Value |
|-------|-------|
| Command | `uv run pytest -q` |
| Exit code | `1` |
| Passed | 628 |
| Failed | 1 |
| Warnings | 2 (StarletteDeprecationWarning + zipfile duplicate name warning — unrelated) |

The single failure is the same `test_only_intake_route_registered` from Run 1. All 628 other tests pass.

---

## compileall Check

| Field | Value |
|-------|-------|
| Command | `uv run python -m compileall -q app tests` |
| Exit code | `0` |
| Result | **PASS** — all Python modules compile without syntax errors |

---

## git diff --check

| Field | Value |
|-------|-------|
| Command | `git diff --check` |
| Exit code | `0` |
| Result | **PASS** — no whitespace or formatting warnings |

---

## Summary Table

| Check | Exit Code | Result |
|-------|-----------|--------|
| Targeted pytest (2 files) | `1` | 5 passed, 1 failed |
| Full pytest (all) | `1` | 628 passed, 1 failed |
| compileall | `0` | PASS |
| git diff --check | `0` | PASS |

---

## Overall Result

**FAIL** — One test failure prevents overall PASS.

| Field | Value |
|-------|-------|
| Status | **FAIL** |
| Total tests | 629 |
| Passed | 628 |
| Failed | 1 |
| Failed test | `tests/test_private_intake_entrypoint.py::test_only_intake_route_registered` |
| Blocker | Test code defect: does not handle `_IncludedRouter` objects in `app.routes` |

---

## Blocker Analysis

The `app/intake_only.py` module correctly uses `include_router()` to mount the commercial intake router. However, `test_only_intake_entrypoint.py` iterates `app.routes` directly, expecting each element to have a `.path` attribute. FastAPI's `include_router()` wraps the included router in an `_IncludedRouter` object that does not expose `.path` at the top level.

**Fix required in test code (not authorized by this WP):** The test should either:
- Filter routes to only those with a `.path` attribute, or
- Access the included router's inner routes via `route.routes` for `_IncludedRouter` instances, or
- Use `TestClient` to verify the endpoint exists rather than inspecting `app.routes` directly.

Per spec: "Do not change code/tests to force PASS." No changes were made.

---

## Prohibitions Compliance

| Prohibition | Status |
|-------------|--------|
| No code/test changes | ✅ Complied |
| No `.env` or live database access | ✅ Complied |
| No containers or services started | ✅ Complied |
| No Docker/network/n8n modification | ✅ Complied |
| No workflow activation/import | ✅ Complied |
| No migrations | ✅ Complied |
| No merge | ✅ Complied |
| No other WP | ✅ Complied |

---

## Cleanup

- Temporary clone `/tmp/wp-043-temp-clone` to be discarded.
- No containers, networks, or services were modified.
- No credentials, workflows, or environment variables were read or changed.
- No `.env`, docker-compose, or secret files were accessed.

---

## Next Steps (Not Authorized by This WP)

A future WP may fix `test_only_intake_route_registered` to correctly handle `_IncludedRouter` objects in FastAPI's route list, then re-run validation to achieve full PASS.

**STOP.** No code changes, no merge, no other WP authorized by WP-043.
