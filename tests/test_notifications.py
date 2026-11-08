"""WP-524 — Notifications endpoint tests."""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opportunity"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": "manual",
            "external_url": f"https://example.com/{title.replace(' ', '-')}",
            "title": title,
            "description": "Test description",
            "budget": "R$ 5000",
            "deadline": "2026-12-31",
            "requirements": "Python",
            "captured_at": "2026-01-01T12:00:00Z",
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Basic notifications ---


def test_notifications_returns_structure(client, admin_headers, operator_a_headers):
    """Notifications returns correct structure."""
    company = _create_company(client, admin_headers, name="NotifCo")

    res = client.get(
        f"/companies/{company['id']}/notifications",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "notifications" in data
    assert "unread_count" in data


def test_notifications_new_opportunity(client, admin_headers, operator_a_headers):
    """Notifications includes new opportunities."""
    company = _create_company(client, admin_headers, name="NewOppCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="New Opp")

    res = client.get(
        f"/companies/{company['id']}/notifications",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    new_opps = [n for n in data["notifications"] if n["notification_type"] == "new_opportunity"]
    assert len(new_opps) >= 1


def test_notifications_empty(client, admin_headers, operator_a_headers):
    """Notifications returns empty for company with no activity."""
    company = _create_company(client, admin_headers, name="EmptyNotifCo")

    res = client.get(
        f"/companies/{company['id']}/notifications",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["notifications"] == []
    assert data["unread_count"] == 0


def test_notifications_has_required_fields(client, admin_headers, operator_a_headers):
    """Each notification has required fields."""
    company = _create_company(client, admin_headers, name="FieldsNotifCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Field Test")

    res = client.get(
        f"/companies/{company['id']}/notifications",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    for notif in data["notifications"]:
        assert "notification_type" in notif
        assert "entity_id" in notif
        assert "title" in notif
        assert "timestamp" in notif
        assert "read" in notif


# --- Limit ---


def test_notifications_limit(client, admin_headers, operator_a_headers):
    """Notifications respects limit parameter."""
    company = _create_company(client, admin_headers, name="LimitNotifCo")
    for i in range(5):
        _create_opportunity(client, operator_a_headers, company["id"], title=f"Opp {i}")

    res = client.get(
        f"/companies/{company['id']}/notifications?limit=2",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["notifications"]) <= 2


# --- Tenant isolation ---


def test_notifications_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot see Operator B's notifications."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    company_b = _create_company(client, admin_headers, name="TenantB")

    res = client.get(
        f"/companies/{company_b['id']}/notifications",
        headers=operator_a_headers,
    )
    assert res.status_code == 403


# --- Auth requirements ---


def test_notifications_requires_auth(client):
    """Notifications requires authentication."""
    res = client.get("/companies/1/notifications")
    assert res.status_code in (401, 403)


def test_notifications_company_not_found(client, admin_headers, operator_a_headers):
    """Notifications returns 404 for non-existent company."""
    res = client.get(
        "/companies/99999/notifications",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
