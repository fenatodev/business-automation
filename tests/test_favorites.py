"""WP-521 — Favorites endpoint tests."""


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


# --- Opportunity favorite ---


def test_favorite_opportunity(client, admin_headers, operator_a_headers):
    """Toggle favorite on an opportunity."""
    company = _create_company(client, admin_headers, name="FavOppCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], title="Fav Opp")

    res = client.patch(
        f"/opportunities/{opp['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["entity_type"] == "opportunity"
    assert data["entity_id"] == opp["id"]
    assert data["favorited"] is True
    assert data["favorited_at"] is not None


def test_unfavorite_opportunity(client, admin_headers, operator_a_headers):
    """Remove favorite from an opportunity."""
    company = _create_company(client, admin_headers, name="UnfavOppCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], title="Unfav Opp")

    # Favorite first
    client.patch(
        f"/opportunities/{opp['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    # Then unfavorite
    res = client.patch(
        f"/opportunities/{opp['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["favorited"] is False
    assert data["favorited_at"] is None


def test_favorite_opportunity_not_found(client, admin_headers, operator_a_headers):
    """Favorite non-existent opportunity returns 404."""
    res = client.patch(
        "/opportunities/99999/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    assert res.status_code == 404


# --- Conversation favorite ---


def test_favorite_conversation(client, admin_headers, operator_a_headers):
    """Toggle favorite on a conversation."""
    company = _create_company(client, admin_headers, name="FavConvCo")
    conv = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")

    res = client.patch(
        f"/conversations/{conv['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["entity_type"] == "conversation"
    assert data["entity_id"] == conv["id"]
    assert data["favorited"] is True
    assert data["favorited_at"] is not None


def test_unfavorite_conversation(client, admin_headers, operator_a_headers):
    """Remove favorite from a conversation."""
    company = _create_company(client, admin_headers, name="UnfavConvCo")
    conv = _create_conversation(client, operator_a_headers, company["id"], channel="instagram")

    client.patch(
        f"/conversations/{conv['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    res = client.patch(
        f"/conversations/{conv['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["favorited"] is False
    assert data["favorited_at"] is None


def test_favorite_conversation_not_found(client, admin_headers, operator_a_headers):
    """Favorite non-existent conversation returns 404."""
    res = client.patch(
        "/conversations/99999/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    assert res.status_code == 404


# --- Tenant isolation ---


def test_favorite_opportunity_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot favorite Operator B's opportunity."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    company_b = _create_company(client, admin_headers, name="TenantB")

    opp_b = _create_opportunity(client, operator_b_headers, company_b["id"], title="B Opp")

    res = client.patch(
        f"/opportunities/{opp_b['id']}/favorite",
        headers=operator_a_headers,
        json={"favorited": True},
    )
    assert res.status_code == 404


# --- Auth requirements ---


def test_favorite_opportunity_requires_auth(client):
    """Favorite requires authentication."""
    res = client.patch(
        "/opportunities/1/favorite",
        json={"favorited": True},
    )
    assert res.status_code in (401, 403)


def test_favorite_conversation_requires_auth(client):
    """Favorite requires authentication."""
    res = client.patch(
        "/conversations/1/favorite",
        json={"favorited": True},
    )
    assert res.status_code in (401, 403)


# --- Validation ---


def test_favorite_opportunity_invalid_body(client, admin_headers, operator_a_headers):
    """Favorite with invalid body returns 422."""
    company = _create_company(client, admin_headers, name="ValidCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], title="Valid Opp")

    res = client.patch(
        f"/opportunities/{opp['id']}/favorite",
        headers=operator_a_headers,
        json={"invalid": True},
    )
    assert res.status_code == 422
