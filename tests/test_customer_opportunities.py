"""Customer opportunities endpoint tests.

Tests the GET /customers/{customer_id}/opportunities endpoint that returns
all opportunities related to a customer (directly linked or via converted lead).
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_customer(client, headers, company_id, name="Test Customer", phone="+5511999999999"):
    res = client.post(
        "/customers",
        headers=headers,
        json={"company_id": company_id, "name": name, "phone": phone},
    )
    assert res.status_code == 200, f"Failed to create customer: {res.text}"
    return res.json()


def _create_lead(client, headers, company_id, name="Test Lead", phone="+5511988888888"):
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
    assert res.status_code == 200, f"Failed to create lead: {res.text}"
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opportunity", customer_id=None, lead_id=None):
    from datetime import datetime, timezone
    payload = {
        "company_id": company_id,
        "source": "manual",
        "external_url": f"https://example.com/{title.lower().replace(' ', '-')}",
        "title": title,
        "description": "Test description",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if customer_id:
        payload["customer_id"] = customer_id
    if lead_id:
        payload["lead_id"] = lead_id
    res = client.post("/opportunities", headers=headers, json=payload)
    assert res.status_code == 200, f"Failed to create opportunity: {res.text}"
    return res.json()


def test_empty_when_no_opportunities(client, admin_headers, operator_a_headers):
    """Returns empty when customer has no opportunities."""
    company = _create_company(client, admin_headers, name="EmptyCo")
    customer = _create_customer(client, operator_a_headers, company["id"])

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["opportunities"] == []


def test_returns_directly_linked_opportunities(client, admin_headers, operator_a_headers):
    """Returns opportunities linked directly via customer_id."""
    company = _create_company(client, admin_headers, name="DirectCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    opp = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Direct Opp", customer_id=customer["id"],
    )

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["opportunities"][0]["opportunity_id"] == opp["id"]
    assert data["opportunities"][0]["title"] == "Direct Opp"


def test_returns_opportunities_via_converted_lead(client, admin_headers, operator_a_headers):
    """Returns opportunities linked via lead with same phone as customer."""
    phone = "+5511977777777"
    company = _create_company(client, admin_headers, name="LeadCo")
    lead = _create_lead(client, operator_a_headers, company["id"], phone=phone)
    _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Lead Opp", lead_id=lead["id"],
    )
    # Customer created with same phone (simulates conversion)
    customer = _create_customer(client, operator_a_headers, company["id"], phone=phone)

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["opportunities"][0]["title"] == "Lead Opp"


def test_returns_both_direct_and_lead_opportunities(client, admin_headers, operator_a_headers):
    """Returns both direct and lead-linked opportunities."""
    phone = "+5511966666666"
    company = _create_company(client, admin_headers, name="BothCo")
    customer = _create_customer(client, operator_a_headers, company["id"], phone=phone)

    _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Direct Opp", customer_id=customer["id"],
    )
    lead = _create_lead(client, operator_a_headers, company["id"], phone=phone)
    _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Lead Opp", lead_id=lead["id"],
    )

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    titles = {opp["title"] for opp in data["opportunities"]}
    assert "Direct Opp" in titles
    assert "Lead Opp" in titles


def test_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Opportunities are isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    customer_b = _create_customer(client, operator_b_headers, 2)
    _create_opportunity(
        client, operator_b_headers, 2,
        title="TenantB Opp", customer_id=customer_b["id"],
    )

    # Operator A sees nothing
    res_a = client.get(
        f"/customers/{customer_b['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res_a.status_code == 404  # customer not in tenant A


def test_404_when_customer_not_found(client, operator_a_headers):
    """Returns 404 for non-existent customer."""
    res = client.get(
        "/customers/99999/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/customers/1/opportunities")
    assert res.status_code == 401


def test_response_contains_required_fields(client, admin_headers, operator_a_headers):
    """Response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Fields Opp", customer_id=customer["id"],
    )

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert "opportunities" in data
    assert "total" in data

    item = data["opportunities"][0]
    assert "opportunity_id" in item
    assert "title" in item
    assert "source" in item
    assert "next_action" in item
    assert "outcome" in item
    assert "budget" in item
    assert "deadline" in item
    assert "created_at" in item


def test_multiple_opportunities_sorted_by_id(client, admin_headers, operator_a_headers):
    """Multiple opportunities are sorted by ID ascending."""
    company = _create_company(client, admin_headers, name="MultiCo")
    customer = _create_customer(client, operator_a_headers, company["id"])

    opp1 = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="First Opp", customer_id=customer["id"],
    )
    opp2 = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Second Opp", customer_id=customer["id"],
    )
    opp3 = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Third Opp", customer_id=customer["id"],
    )

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    ids = [opp["opportunity_id"] for opp in data["opportunities"]]
    assert ids == sorted(ids)


def test_includes_opportunity_outcome(client, admin_headers, operator_a_headers):
    """Response includes outcome field for closed opportunities."""
    company = _create_company(client, admin_headers, name="OutcomeCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    opp = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Won Opp", customer_id=customer["id"],
    )

    # Close the opportunity as won
    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won", "reason": "Client accepted"},
    )
    assert res.status_code == 200

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["opportunities"][0]["outcome"] == "won"


def test_no_duplicate_when_opportunity_has_both_lead_and_customer(
    client, admin_headers, operator_a_headers,
):
    """Does not duplicate opportunity when it has both lead_id and customer_id."""
    phone = "+5511955555555"
    company = _create_company(client, admin_headers, name="NoDupCo")
    customer = _create_customer(client, operator_a_headers, company["id"], phone=phone)
    lead = _create_lead(client, operator_a_headers, company["id"], phone=phone)

    # Create opportunity with customer_id; the lead has same phone but opp
    # is not linked to the lead, so no duplication
    _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Single Opp", customer_id=customer["id"],
    )

    res = client.get(
        f"/customers/{customer['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1


def test_customer_from_other_tenant_returns_404(
    client, admin_headers, operator_a_headers, operator_b_headers,
):
    """Customer from another tenant returns 404."""
    _create_company(client, admin_headers, name="IsolatedA")
    _create_company(client, admin_headers, name="IsolatedB")

    customer_b = _create_customer(client, operator_b_headers, 2)

    res = client.get(
        f"/customers/{customer_b['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
