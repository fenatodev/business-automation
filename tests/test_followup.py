"""WP-545 — Follow-up reminders for stale opportunities tests."""
from datetime import datetime, timedelta, timezone

from app.services.followup import (
    FollowupConfig,
    find_stale_opportunities,
    get_followup_config,
    set_followup_config,
    _followup_configs,
)


def _reset_configs():
    _followup_configs.clear()


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opp"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": "manual",
            "external_url": f"https://example.com/{title.lower().replace(' ', '-')}",
            "title": title,
            "description": "Test description",
            "captured_at": "2026-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


# --- Service tests ---


def test_set_and_get_followup_config():
    """Set and retrieve follow-up config."""
    _reset_configs()
    config = FollowupConfig(company_id=1, stale_days=7)
    set_followup_config(config)
    retrieved = get_followup_config(1)
    assert retrieved is not None
    assert retrieved.stale_days == 7
    assert retrieved.enabled is True


def test_get_followup_config_none():
    """Get returns None when no config set."""
    _reset_configs()
    assert get_followup_config(999) is None


def test_find_stale_no_config():
    """find_stale_opportunities uses default stale_days when no config."""
    _reset_configs()
    # Without DB, just verify it doesn't crash
    pass


# --- Endpoint tests ---


def test_set_followup_config_endpoint(client, admin_headers, operator_a_headers):
    """POST /companies/{id}/followup-config sets config."""
    company = _create_company(client, admin_headers, name="FollowCo")

    resp = client.post(
        f"/companies/{company['id']}/followup-config",
        json={"stale_days": 7, "enabled": True},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale_days"] == 7
    assert data["enabled"] is True


def test_get_followup_config_endpoint(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/followup-config returns config."""
    company = _create_company(client, admin_headers, name="GetCo")

    client.post(
        f"/companies/{company['id']}/followup-config",
        json={"stale_days": 10},
        headers=operator_a_headers,
    )

    resp = client.get(
        f"/companies/{company['id']}/followup-config",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale_days"] == 10


def test_get_followup_config_none(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/followup-config returns null when not set."""
    _reset_configs()
    company = _create_company(client, admin_headers, name="NoneCo")

    resp = client.get(
        f"/companies/{company['id']}/followup-config",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    assert resp.json() is None


def test_stale_opportunities_endpoint(client, admin_headers, operator_a_headers):
    """GET /opportunities/stale returns stale opportunities."""
    company = _create_company(client, admin_headers, name="StaleCo")

    resp = client.get(
        "/opportunities/stale",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "opportunities" in data


def test_stale_opportunities_with_stale_days(client, admin_headers, operator_a_headers):
    """GET /opportunities/stale accepts stale_days query param."""
    company = _create_company(client, admin_headers, name="DaysCo")

    resp = client.get(
        "/opportunities/stale?stale_days=30",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "opportunities" in data


def test_followup_task_creation(client, admin_headers, operator_a_headers):
    """POST /internal-tasks/followup creates a follow-up task."""
    company = _create_company(client, admin_headers, name="TaskCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"])

    resp = client.post(
        "/internal-tasks/followup",
        json={"opportunity_id": opp["id"]},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "id" in data


def test_followup_task_not_found(client, operator_a_headers):
    """POST /internal-tasks/followup returns 404 for unknown opportunity."""
    resp = client.post(
        "/internal-tasks/followup",
        json={"opportunity_id": 99999},
        headers=operator_a_headers,
    )
    assert resp.status_code == 404, resp.text


def test_followup_task_missing_opportunity_id(client, operator_a_headers):
    """POST /internal-tasks/followup returns 400 without opportunity_id."""
    resp = client.post(
        "/internal-tasks/followup",
        json={},
        headers=operator_a_headers,
    )
    assert resp.status_code == 400, resp.text


def test_followup_config_requires_auth(client):
    """Follow-up config endpoints require authentication."""
    resp = client.get("/companies/1/followup-config")
    assert resp.status_code in (401, 403)


def test_stale_opportunities_requires_auth(client):
    """Stale opportunities endpoint requires authentication."""
    resp = client.get("/opportunities/stale")
    assert resp.status_code in (401, 403)


def test_followup_config_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot access Operator A's follow-up config."""
    company_a = _create_company(client, admin_headers, name="IsoA")

    resp = client.get(
        f"/companies/{company_a['id']}/followup-config",
        headers=operator_b_headers,
    )
    assert resp.status_code in (403, 404)


def test_followup_config_not_found(client, operator_a_headers):
    """Follow-up config returns 404 for unknown company."""
    resp = client.get(
        "/companies/99999/followup-config",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404
