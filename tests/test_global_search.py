"""WP-520 — Global search endpoint tests."""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opportunity", source="manual"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": source,
            "external_url": f"https://example.com/{title.replace(' ', '-')}",
            "title": title,
            "description": "Test description for search",
            "budget": "R$ 5000",
            "deadline": "2026-12-31",
            "requirements": "Python, FastAPI",
            "captured_at": "2026-01-01T12:00:00Z",
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Test Lead", phone="11999999999"):
    res = client.post(
        "/leads",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": phone,
            "source": "manual",
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_customer(client, headers, company_id, name="Test Customer", phone="11888888888"):
    res = client.post(
        "/customers",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": phone,
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, headers, company_id, channel="whatsapp", customer_id=None):
    # Create a customer first for the conversation
    customer = _create_customer(client, headers, company_id, name=f"Customer for {channel}")
    payload = {
        "company_id": company_id,
        "channel": channel,
        "customer_id": customer["id"],
    }
    res = client.post(
        "/conversations",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    return res.json()


# --- Basic search ---


def test_global_search_returns_all_entity_types(client, admin_headers, operator_a_headers):
    """Search returns response with all entity type keys."""
    company = _create_company(client, admin_headers, name="SearchCo")

    res = client.get(
        f"/companies/{company['id']}/search?q=test",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "opportunities" in data
    assert "conversations" in data
    assert "leads" in data
    assert "customers" in data


def test_global_search_finds_opportunity_by_title(client, admin_headers, operator_a_headers):
    """Search finds opportunities by title."""
    company = _create_company(client, admin_headers, name="OppCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Website Project")

    res = client.get(
        f"/companies/{company['id']}/search?q=website",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["opportunities"]) == 1
    assert data["opportunities"][0]["entity_type"] == "opportunity"
    assert "Website" in data["opportunities"][0]["title"]


def test_global_search_finds_opportunity_by_description(client, admin_headers, operator_a_headers):
    """Search finds opportunities by description."""
    company = _create_company(client, admin_headers, name="DescCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="X")

    res = client.get(
        f"/companies/{company['id']}/search?q=description",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["opportunities"]) == 1


def test_global_search_finds_lead_by_name(client, admin_headers, operator_a_headers):
    """Search finds leads by name."""
    company = _create_company(client, admin_headers, name="LeadCo")
    _create_lead(client, operator_a_headers, company["id"], name="Maria Silva")

    res = client.get(
        f"/companies/{company['id']}/search?q=maria",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["leads"]) == 1
    assert data["leads"][0]["entity_type"] == "lead"
    assert "Maria" in data["leads"][0]["title"]


def test_global_search_finds_lead_by_phone(client, admin_headers, operator_a_headers):
    """Search finds leads by phone."""
    company = _create_company(client, admin_headers, name="PhoneCo")
    _create_lead(client, operator_a_headers, company["id"], name="Joao", phone="11912345678")

    res = client.get(
        f"/companies/{company['id']}/search?q=12345",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["leads"]) == 1


def test_global_search_finds_customer_by_name(client, admin_headers, operator_a_headers):
    """Search finds customers by name."""
    company = _create_company(client, admin_headers, name="CustCo")
    _create_customer(client, operator_a_headers, company["id"], name="Empresa ABC")

    res = client.get(
        f"/companies/{company['id']}/search?q=abc",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["customers"]) == 1
    assert data["customers"][0]["entity_type"] == "customer"


def test_global_search_finds_conversation_by_channel(client, admin_headers, operator_a_headers):
    """Search finds conversations by channel."""
    company = _create_company(client, admin_headers, name="ConvCo")
    _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")

    res = client.get(
        f"/companies/{company['id']}/search?q=whatsapp",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["conversations"]) == 1
    assert data["conversations"][0]["entity_type"] == "conversation"


# --- Empty results ---


def test_global_search_empty_result(client, admin_headers, operator_a_headers):
    """Search with no matches returns empty lists."""
    company = _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        f"/companies/{company['id']}/search?q=nonexistent",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["opportunities"] == []
    assert data["conversations"] == []
    assert data["leads"] == []
    assert data["customers"] == []


# --- Limit parameter ---


def test_global_search_limit(client, admin_headers, operator_a_headers):
    """Search respects limit parameter."""
    company = _create_company(client, admin_headers, name="LimitCo")
    for i in range(5):
        _create_opportunity(client, operator_a_headers, company["id"], title=f"Project {i}")

    res = client.get(
        f"/companies/{company['id']}/search?q=project&limit=2",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["opportunities"]) == 2


# --- Case insensitive ---


def test_global_search_case_insensitive(client, admin_headers, operator_a_headers):
    """Search is case insensitive."""
    company = _create_company(client, admin_headers, name="CaseCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Website Project")

    for query in ["WEBSITE", "Website", "website"]:
        res = client.get(
            f"/companies/{company['id']}/search?q={query}",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["opportunities"]) == 1, f"Failed for query: {query}"


# --- Tenant isolation ---


def test_global_search_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot search Operator B's data."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    company_b = _create_company(client, admin_headers, name="TenantB")

    _create_opportunity(client, operator_a_headers, company_a["id"], title="Secret Project")
    _create_opportunity(client, operator_b_headers, company_b["id"], title="Secret Project")

    res_a = client.get(
        f"/companies/{company_a['id']}/search?q=secret",
        headers=operator_a_headers,
    )
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert len(data_a["opportunities"]) == 1

    res_b = client.get(
        f"/companies/{company_b['id']}/search?q=secret",
        headers=operator_b_headers,
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert len(data_b["opportunities"]) == 1


# --- Auth requirements ---


def test_global_search_requires_auth(client):
    """Search requires authentication."""
    res = client.get("/companies/1/search?q=test")
    assert res.status_code in (401, 403)


def test_global_search_forbidden_other_company(client, admin_headers, operator_a_headers):
    """Operator cannot search another company's data via company_id."""
    company_a = _create_company(client, admin_headers, name="ForbiddenA")
    company_b = _create_company(client, admin_headers, name="ForbiddenB")

    res = client.get(
        f"/companies/{company_b['id']}/search?q=test",
        headers=operator_a_headers,
    )
    assert res.status_code == 403


# --- Query validation ---


def test_global_search_query_too_short(client, admin_headers, operator_a_headers):
    """Search requires non-empty query."""
    company = _create_company(client, admin_headers, name="ValidCo")

    res = client.get(
        f"/companies/{company['id']}/search?q=",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_global_search_company_not_found(client, admin_headers, operator_a_headers):
    """Search returns 404 for non-existent company."""
    res = client.get(
        "/companies/99999/search?q=test",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
