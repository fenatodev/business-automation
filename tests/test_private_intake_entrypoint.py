"""Minimal private ASGI surface must exclude all other application routers."""
from app.intake_only import app


def test_only_intake_route_registered():
    paths = [(route.path, getattr(route, "methods", None)) for route in app.routes]
    assert paths == [("/internal/commercial-intake/evaluate", {"POST"})]


def test_private_docs_disabled():
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
