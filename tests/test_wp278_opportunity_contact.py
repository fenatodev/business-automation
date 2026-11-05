"""WP-278: opportunity contact ownership and conversation creation."""

from datetime import datetime, timezone
from pathlib import Path


def _company_and_lead(client, admin_headers, operator_headers, suffix="a"):
    company = client.post("/companies", headers=admin_headers,
                          json={"name": f"Contact {suffix}", "slug": f"contact-{suffix}"})
    assert company.status_code == 200
    cid = company.json()["id"]
    lead = client.post("/leads", headers=operator_headers, json={
        "company_id": cid, "name": "Opportunity Lead", "phone": "5511999999999",
        "source": "manual", "interest": "synthetic",
    })
    assert lead.status_code == 200
    return cid, lead.json()["id"]


def _opportunity(client, headers, lead_id=None):
    body = {
        "source": "manual", "external_url": "https://example.test/wp278",
        "title": "Synthetic opportunity", "description": "Synthetic description",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if lead_id is not None:
        body["lead_id"] = lead_id
    return client.post("/opportunities", headers=headers, json=body)


def test_opportunity_contact_creates_conversation_and_suggestion(
    client, admin_headers, operator_a_headers,
):
    _, lead_id = _company_and_lead(client, admin_headers, operator_a_headers)
    opportunity = _opportunity(client, operator_a_headers, lead_id)
    assert opportunity.status_code == 200
    assert opportunity.json()["lead_id"] == lead_id
    assert [lead["id"] for lead in client.get(
        f"/opportunities/{opportunity.json()['id']}/linked-leads", headers=operator_a_headers,
    ).json()] == [lead_id]
    conversation = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": 1, "channel": "web", "lead_id": lead_id,
    })
    assert conversation.status_code == 200
    assert conversation.json()["lead_id"] == lead_id


def test_opportunity_rejects_cross_tenant_contact(
    client, admin_headers, operator_a_headers, operator_b_headers,
):
    _company_and_lead(client, admin_headers, operator_a_headers, "a-cross")
    _, lead_id = _company_and_lead(client, admin_headers, operator_b_headers, "b-cross")
    response = _opportunity(client, operator_a_headers, lead_id)
    assert response.status_code == 404


def test_opportunity_rejects_two_contacts(client, admin_headers, operator_a_headers):
    _, lead_id = _company_and_lead(client, admin_headers, operator_a_headers, "both")
    payload = {
        "source": "manual", "external_url": "https://example.test/wp278-both",
        "title": "Synthetic opportunity", "description": "Synthetic description",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "lead_id": lead_id, "customer_id": 999,
    }
    assert client.post("/opportunities", headers=operator_a_headers, json=payload).status_code == 422


def test_customer_contact_and_cross_tenant_update(
    client, admin_headers, operator_a_headers, operator_b_headers,
):
    company_a, _ = _company_and_lead(client, admin_headers, operator_a_headers, "customer")
    customer = client.post("/customers", headers=operator_a_headers, json={
        "company_id": company_a, "name": "Synthetic Customer", "phone": "5511888888888",
    })
    assert customer.status_code == 200
    opportunity = _opportunity(client, operator_a_headers)
    assert client.patch(f"/opportunities/{opportunity.json()['id']}", headers=operator_a_headers,
                        json={"customer_id": customer.json()["id"]}).status_code == 200
    assert client.get(f"/opportunities/{opportunity.json()['id']}/linked-leads",
                      headers=operator_a_headers).json() == []

    _, foreign_lead = _company_and_lead(client, admin_headers, operator_b_headers, "foreign-update")
    response = client.patch(f"/opportunities/{opportunity.json()['id']}", headers=operator_a_headers,
                            json={"lead_id": foreign_lead})
    assert response.status_code == 404


def test_linked_customer_endpoint_is_tenant_scoped(
    client, admin_headers, operator_a_headers,
):
    company, _ = _company_and_lead(client, admin_headers, operator_a_headers, "customer-linked")
    customer = client.post("/customers", headers=operator_a_headers, json={
        "company_id": company, "name": "Linked Customer", "phone": "5511777777777",
    })
    opportunity = _opportunity(client, operator_a_headers)
    updated = client.patch(f"/opportunities/{opportunity.json()['id']}", headers=operator_a_headers,
                           json={"customer_id": customer.json()["id"]})
    assert updated.status_code == 200
    linked = client.get(f"/opportunities/{opportunity.json()['id']}/linked-customers",
                        headers=operator_a_headers)
    assert linked.status_code == 200
    assert [item["id"] for item in linked.json()] == [customer.json()["id"]]


def test_ui_uses_linked_contact_and_authenticated_conversation_routes():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert '/opportunities/" + id + "/linked-leads' in js
    assert 'conversationApi("/conversations/suggest-message", "POST"' in js
    assert 'conversationApi("/conversations/", "POST"' in js
    assert 'channel: $("opp-conv-channel").value' in js
    assert "expectedVersion !== selectionVersion" in js
    assert "opportunityLeadId = null" in js
    assert "if (version !== selectionVersion || selectedId === null) return;" in js
    assert "oppConvSuggestion.__version === selectionVersion" in js
    assert 'hidden = opportunityContactType === null' in js
    customer_submit = js[js.index('$("customer-opp-form").addEventListener'):]
    assert 'customer_id: currentCustomerId' in customer_submit


def test_ui_shows_customer_context_in_portuguese():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'const parts = ["Cliente"]' in js
    assert 'if (customer.phone) parts.push(customer.phone)' in js
    assert 'if (customer.status) parts.push("(" + customer.status + ")")' in js
    assert 'item.addEventListener("keydown", (event) => {' in js
    assert 'const openDetail = showCustomerDeta\\u0069l' in js
    assert 'item.addEventListener("keydown", (event) => {' in js
    assert 'showLeadDetail(lead)' in js
    assert 'item.setAttribute("aria-label", "Abrir lead "' in js
    assert 'item.setAttribute("aria-label", "Abrir cliente "' in js
    assert 'item.setAttribute("role", "listitem")' in js
