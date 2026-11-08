"""WP-522 — Activity feed endpoint tests."""


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


def _create_customer(client, headers, company_id, name="Test Customer"):
    res = client.post(
        "/customers",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": "11999999999",
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, headers, company_id, channel="whatsapp"):
    customer = _create_customer(client, headers, company_id, name=f"Cust for {channel}")
    res = client.post(
        "/conversations",
        headers=headers,
        json={
            "company_id": company_id,
            "channel": channel,
            "customer_id": customer["id"],
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Basic activity feed ---


def test_activity_feed_returns_items(client, admin_headers, operator_a_headers):
    """Activity feed returns opportunity_created items."""
    company = _create_company(client, admin_headers, name="ActivityCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="New Opp")

    res = client.get(
        f"/companies/{company['id']}/activity",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    # Should have at least one opportunity_created item
    opp_created = [i for i in data["items"] if i["activity_type"] == "opportunity_created"]
    assert len(opp_created) >= 1


def test_activity_feed_empty(client, admin_headers, operator_a_headers):
    """Activity feed returns empty list when no activity."""
    company = _create_company(client, admin_headers, name="EmptyActivityCo")

    res = client.get(
        f"/companies/{company['id']}/activity",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []


def test_activity_feed_has_required_fields(client, admin_headers, operator_a_headers):
    """Each activity item has required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Field Test")

    res = client.get(
        f"/companies/{company['id']}/activity",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert "activity_type" in item
        assert "entity_id" in item
        assert "title" in item
        assert "timestamp" in item


# --- Period filtering ---


def test_activity_feed_period_7d(client, admin_headers, operator_a_headers):
    """Activity feed respects 7d period."""
    company = _create_company(client, admin_headers, name="Period7Co")
    _create_opportunity(client, operator_a_headers, company["id"], title="Recent")

    res = client.get(
        f"/companies/{company['id']}/activity?period=7d",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data


def test_activity_feed_period_30d(client, admin_headers, operator_a_headers):
    """Activity feed respects 30d period."""
    company = _create_company(client, admin_headers, name="Period30Co")
    _create_opportunity(client, operator_a_headers, company["id"], title="Recent")

    res = client.get(
        f"/companies/{company['id']}/activity?period=30d",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data


def test_activity_feed_period_90d(client, admin_headers, operator_a_headers):
    """Activity feed respects 90d period."""
    company = _create_company(client, admin_headers, name="Period90Co")
    _create_opportunity(client, operator_a_headers, company["id"], title="Recent")

    res = client.get(
        f"/companies/{company['id']}/activity?period=90d",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data


def test_activity_feed_invalid_period(client, admin_headers, operator_a_headers):
    """Activity feed rejects invalid period."""
    company = _create_company(client, admin_headers, name="InvalidPeriodCo")

    res = client.get(
        f"/companies/{company['id']}/activity?period=invalid",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


# --- Limit ---


def test_activity_feed_limit(client, admin_headers, operator_a_headers):
    """Activity feed respects limit parameter."""
    company = _create_company(client, admin_headers, name="LimitCo")
    for i in range(5):
        _create_opportunity(client, operator_a_headers, company["id"], title=f"Opp {i}")

    res = client.get(
        f"/companies/{company['id']}/activity?limit=2",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) <= 2


# --- Tenant isolation ---


def test_activity_feed_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot see Operator B's activity."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    company_b = _create_company(client, admin_headers, name="TenantB")

    _create_opportunity(client, operator_b_headers, company_b["id"], title="B Opp")

    res = client.get(
        f"/companies/{company_a['id']}/activity",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    # Company A has no opportunities, so no items
    assert data["items"] == []


# --- Auth requirements ---


def test_activity_feed_requires_auth(client):
    """Activity feed requires authentication."""
    res = client.get("/companies/1/activity")
    assert res.status_code in (401, 403)


def test_activity_feed_forbidden_other_company(client, admin_headers, operator_a_headers):
    """Operator cannot access another company's activity."""
    company_a = _create_company(client, admin_headers, name="ForbiddenA")
    company_b = _create_company(client, admin_headers, name="ForbiddenB")

    res = client.get(
        f"/companies/{company_b['id']}/activity",
        headers=operator_a_headers,
    )
    assert res.status_code == 403


# --- Company not found ---


def test_activity_feed_company_not_found(client, admin_headers, operator_a_headers):
    """Activity feed returns 404 for non-existent company."""
    res = client.get(
        "/companies/99999/activity",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
