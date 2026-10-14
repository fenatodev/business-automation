"""Assert private ASGI reachability without FastAPI route internals."""
from fastapi.testclient import TestClient
from app.intake_only import app


def test_private_entrypoint_exposes_only_expected_http_surface():
    client = TestClient(app)
    # Protected endpoint must be mounted; unauthenticated POST is rejected.
    assert client.post(
        "/internal/commercial-intake/evaluate",
        json={"channel": "test", "event_id": "synthetic", "message": "Oi"},
    ).status_code == 401

    # Every other known application route remains absent in this entrypoint.
    for path in ("/", "/companies", "/leads", "/customers", "/opportunities",
                 "/conversations", "/operator", "/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_private_docs_disabled():
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
