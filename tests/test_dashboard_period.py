"""WP-517 — Dashboard metrics filtered by period (7/30/90 days)."""
from datetime import datetime, timedelta, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Lead"):
    res = client.post(
        "/leads",
        headers=headers,
        json={"company_id": company_id, "name": name, "phone": "5511999999999", "source": "manual"},
    )
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": "manual",
            "external_url": "https://example.com/test",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Period filter tests ---


def test_dashboard_without_period_returns_all(client, admin_headers, operator_a_headers):
    """Dashboard without period param returns all-time metrics."""
    company = _create_company(client, admin_headers, name="AllTimeCo")
    _create_lead(client, operator_a_headers, company["id"], name="Lead1")
    _create_lead(client, operator_a_headers, company["id"], name="Lead2")
    _create_opportunity(client, operator_a_headers, title="Opp1")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["period"] is None
    assert data["leads"]["total"] == 2
    assert data["opportunities"]["total"] == 1


def test_dashboard_with_period_7(client, admin_headers, operator_a_headers):
    """Dashboard with period=7 returns only recent metrics."""
    company = _create_company(client, admin_headers, name="Period7Co")
    _create_lead(client, operator_a_headers, company["id"], name="RecentLead")
    _create_opportunity(client, operator_a_headers, title="RecentOpp")

    res = client.get(
        "/internal-tasks/dashboard?period=7",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == 7
    # All records were just created, so they should be within 7 days
    assert data["leads"]["total"] >= 1
    assert data["opportunities"]["total"] >= 1


def test_dashboard_with_period_30(client, admin_headers, operator_a_headers):
    """Dashboard with period=30 returns metrics from last 30 days."""
    company = _create_company(client, admin_headers, name="Period30Co")
    _create_lead(client, operator_a_headers, company["id"], name="Lead30")

    res = client.get(
        "/internal-tasks/dashboard?period=30",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == 30
    assert data["leads"]["total"] >= 1


def test_dashboard_with_period_90(client, admin_headers, operator_a_headers):
    """Dashboard with period=90 returns metrics from last 90 days."""
    company = _create_company(client, admin_headers, name="Period90Co")
    _create_lead(client, operator_a_headers, company["id"], name="Lead90")

    res = client.get(
        "/internal-tasks/dashboard?period=90",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == 90
    assert data["leads"]["total"] >= 1


def test_dashboard_period_too_small(client, operator_a_headers):
    """Period less than 1 returns 422."""
    res = client.get(
        "/internal-tasks/dashboard?period=0",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_dashboard_period_too_large(client, operator_a_headers):
    """Period greater than 365 returns 422."""
    res = client.get(
        "/internal-tasks/dashboard?period=366",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_dashboard_period_negative(client, operator_a_headers):
    """Negative period returns 422."""
    res = client.get(
        "/internal-tasks/dashboard?period=-1",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_dashboard_period_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Period filter respects tenant isolation."""
    _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")
    _create_lead(client, operator_b_headers, company_b["id"], name="IsoLead")

    res = client.get(
        "/internal-tasks/dashboard?period=7",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    # Operator A should not see Operator B's leads
    assert data["leads"]["total"] == 0


def test_dashboard_period_requires_auth(client):
    """Dashboard with period requires authentication."""
    res = client.get("/internal-tasks/dashboard?period=7")
    assert res.status_code in (401, 403)
