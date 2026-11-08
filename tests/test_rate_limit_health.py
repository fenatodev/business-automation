"""WP-534/535 — Rate limiting and agent health check tests."""
import time

from app.services.rate_limiter import RateLimiter
from app.services.agent import _available_providers, register_provider, NoopProvider, OllamaProvider


def _reset_providers():
    _available_providers.clear()


# --- Rate limiter unit tests ---


def test_rate_limiter_default_limit():
    """Rate limiter uses default limit."""
    rl = RateLimiter(default_limit=10)
    assert rl.get_limit(1) == 10


def test_rate_limiter_custom_limit():
    """Rate limiter supports custom limit per company."""
    rl = RateLimiter()
    rl.set_limit(1, 50)
    assert rl.get_limit(1) == 50
    assert rl.get_limit(2) == 100  # default


def test_rate_limiter_check_allows():
    """Rate limiter check returns True when under limit."""
    rl = RateLimiter(default_limit=5)
    for _ in range(5):
        assert rl.check(1) is True


def test_rate_limiter_check_denies():
    """Rate limiter check returns False when over limit."""
    rl = RateLimiter(default_limit=3)
    for _ in range(3):
        rl.check(1)
    assert rl.check(1) is False


def test_rate_limiter_remaining():
    """Rate limiter tracks remaining quota."""
    rl = RateLimiter(default_limit=5)
    assert rl.remaining(1) == 5
    rl.check(1)
    assert rl.remaining(1) == 4


def test_rate_limiter_status():
    """Rate limiter status returns all fields."""
    rl = RateLimiter(default_limit=10)
    rl.check(1)
    status = rl.status(1)
    assert status["limit"] == 10
    assert status["remaining"] == 9
    assert status["used"] == 1
    assert "reset_in_seconds" in status
    assert "window_seconds" in status


def test_rate_limiter_reset():
    """Rate limiter reset clears quota."""
    rl = RateLimiter(default_limit=3)
    for _ in range(3):
        rl.check(1)
    assert rl.remaining(1) == 0
    rl.reset(1)
    assert rl.remaining(1) == 3


def test_rate_limiter_window_reset():
    """Rate limiter resets after window expires."""
    rl = RateLimiter(default_limit=1, window_seconds=1)
    rl.check(1)
    assert rl.check(1) is False
    time.sleep(1.1)
    assert rl.check(1) is True


# --- Rate limit endpoint tests ---


def test_rate_limit_status_endpoint(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/rate-limit-status returns status."""
    res = client.post("/companies", headers=admin_headers, json={"name": "RateCo", "slug": "rateco"})
    company = res.json()

    res = client.get(
        f"/companies/{company['id']}/rate-limit-status",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "limit" in data
    assert "remaining" in data
    assert "used" in data


def test_rate_limit_status_requires_auth(client):
    """Rate limit status requires authentication."""
    res = client.get("/companies/1/rate-limit-status")
    assert res.status_code in (401, 403)


def test_rate_limit_status_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot check Operator B's rate limit."""
    res = client.post("/companies", headers=admin_headers, json={"name": "IsoCo", "slug": "isoco"})
    company = res.json()

    res = client.get(
        f"/companies/{company['id']}/rate-limit-status",
        headers=operator_b_headers,
    )
    assert res.status_code == 403


# --- Agent health check tests ---


def test_agent_health_endpoint(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/agent-health returns health status."""
    res = client.post("/companies", headers=admin_headers, json={"name": "HealthCo", "slug": "healthco"})
    company = res.json()

    res = client.get(
        f"/companies/{company['id']}/agent-health",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "status" in data


def test_agent_health_noop_provider():
    """NoopProvider health check returns healthy."""
    provider = NoopProvider()
    result = provider.health_check()
    assert result["provider"] == "noop"
    assert result["status"] == "healthy"


def test_agent_health_ollama_unhealthy():
    """OllamaProvider health check returns unhealthy when unavailable."""
    provider = OllamaProvider(base_url="http://localhost:99999")
    result = provider.health_check()
    assert result["provider"] == "ollama"
    assert result["status"] == "unhealthy"


def test_agent_health_uses_registered_provider():
    """Health check uses the registered default provider."""
    _reset_providers()
    register_provider("default", NoopProvider())
    from app.services.agent import get_provider
    provider = get_provider()
    result = provider.health_check()
    assert result["provider"] == "noop"
    assert result["status"] == "healthy"
