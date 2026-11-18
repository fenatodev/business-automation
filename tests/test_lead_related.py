"""Lead conversations and opportunities endpoint tests.

Tests GET /leads/{lead_id}/conversations and GET /leads/{lead_id}/opportunities
endpoints that return related records for a lead.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Test Lead", phone="+5511999999999"):
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


def _create_conversation(client, headers, company_id, lead_id, channel="whatsapp"):
    payload = {
        "company_id": company_id,
        "channel": channel,
        "lead_id": lead_id,
    }
    res = client.post("/conversations", headers=headers, json=payload)
    assert res.status_code == 200, f"Failed to create conversation: {res.text}"
    return res.json()


def _create_message(client, headers, conversation_id, sender_type="customer", content="Hello"):
    res = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={"sender_type": sender_type, "content": content},
    )
    assert res.status_code == 200, f"Failed to create message: {res.text}"
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opportunity", lead_id=None):
    payload = {
        "company_id": company_id,
        "source": "manual",
        "external_url": f"https://example.com/{title.lower().replace(' ', '-')}",
        "title": title,
        "description": "Test description",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if lead_id:
        payload["lead_id"] = lead_id
    res = client.post("/opportunities", headers=headers, json=payload)
    assert res.status_code == 200, f"Failed to create opportunity: {res.text}"
    return res.json()


# --- Conversations tests ---


def test_conversations_empty_when_no_conversations(client, admin_headers, operator_a_headers):
    """Returns empty when lead has no conversations."""
    company = _create_company(client, admin_headers, name="EmptyConvCo")
    lead = _create_lead(client, operator_a_headers, company["id"])

    res = client.get(
        f"/leads/{lead['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["conversations"] == []


def test_conversations_returns_linked_conversations(client, admin_headers, operator_a_headers):
    """Returns conversations linked to the lead."""
    company = _create_company(client, admin_headers, name="ConvCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead["id"])

    res = client.get(
        f"/leads/{lead['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["conversations"][0]["conversation_id"] == conv["id"]
    assert data["conversations"][0]["channel"] == "whatsapp"


def test_conversations_includes_message_count(client, admin_headers, operator_a_headers):
    """Conversation includes message count."""
    company = _create_company(client, admin_headers, name="MsgCountCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead["id"])
    _create_message(client, operator_a_headers, conv["id"], "customer", "Hi")
    _create_message(client, operator_a_headers, conv["id"], "agent", "Hello")

    res = client.get(
        f"/leads/{lead['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["conversations"][0]["message_count"] == 2


def test_conversations_multiple_channels(client, admin_headers, operator_a_headers):
    """Works across different channels."""
    company = _create_company(client, admin_headers, name="MultiChCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_conversation(client, operator_a_headers, company["id"], lead["id"], "whatsapp")
    _create_conversation(client, operator_a_headers, company["id"], lead["id"], "email")

    res = client.get(
        f"/leads/{lead['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    channels = {c["channel"] for c in data["conversations"]}
    assert "whatsapp" in channels
    assert "email" in channels


def test_conversations_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Conversations are isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    lead_b = _create_lead(client, operator_b_headers, 2)
    _create_conversation(client, operator_b_headers, 2, lead_b["id"])

    res_a = client.get(
        f"/leads/{lead_b['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res_a.status_code == 404


def test_conversations_404_when_lead_not_found(client, operator_a_headers):
    """Returns 404 for non-existent lead."""
    res = client.get(
        "/leads/99999/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_conversations_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/leads/1/conversations")
    assert res.status_code == 401


def test_conversations_response_fields(client, admin_headers, operator_a_headers):
    """Response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead["id"])

    res = client.get(
        f"/leads/{lead['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    item = res.json()["conversations"][0]
    assert "conversation_id" in item
    assert "channel" in item
    assert "status" in item
    assert "message_count" in item
    assert "created_at" in item


# --- Opportunities tests ---


def test_opportunities_empty_when_no_opportunities(client, admin_headers, operator_a_headers):
    """Returns empty when lead has no opportunities."""
    company = _create_company(client, admin_headers, name="EmptyOppCo")
    lead = _create_lead(client, operator_a_headers, company["id"])

    res = client.get(
        f"/leads/{lead['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["opportunities"] == []


def test_opportunities_returns_linked_opportunities(client, admin_headers, operator_a_headers):
    """Returns opportunities linked to the lead."""
    company = _create_company(client, admin_headers, name="OppCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    opp = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Lead Opp", lead_id=lead["id"],
    )

    res = client.get(
        f"/leads/{lead['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["opportunities"][0]["opportunity_id"] == opp["id"]
    assert data["opportunities"][0]["title"] == "Lead Opp"


def test_opportunities_multiple_sorted_by_id(client, admin_headers, operator_a_headers):
    """Multiple opportunities are sorted by ID ascending."""
    company = _create_company(client, admin_headers, name="MultiOppCo")
    lead = _create_lead(client, operator_a_headers, company["id"])

    _create_opportunity(client, operator_a_headers, company["id"], title="First", lead_id=lead["id"])
    _create_opportunity(client, operator_a_headers, company["id"], title="Second", lead_id=lead["id"])
    _create_opportunity(client, operator_a_headers, company["id"], title="Third", lead_id=lead["id"])

    res = client.get(
        f"/leads/{lead['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    ids = [o["opportunity_id"] for o in data["opportunities"]]
    assert ids == sorted(ids)


def test_opportunities_includes_outcome(client, admin_headers, operator_a_headers):
    """Response includes outcome for closed opportunities."""
    company = _create_company(client, admin_headers, name="OutcomeCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    opp = _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Won Opp", lead_id=lead["id"],
    )

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won", "reason": "Accepted"},
    )
    assert res.status_code == 200

    res = client.get(
        f"/leads/{lead['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["opportunities"][0]["outcome"] == "won"


def test_opportunities_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Opportunities are isolated per tenant."""
    _create_company(client, admin_headers, name="IsoA")
    _create_company(client, admin_headers, name="IsoB")

    lead_b = _create_lead(client, operator_b_headers, 2)
    _create_opportunity(client, operator_b_headers, 2, title="B Opp", lead_id=lead_b["id"])

    res_a = client.get(
        f"/leads/{lead_b['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res_a.status_code == 404


def test_opportunities_404_when_lead_not_found(client, operator_a_headers):
    """Returns 404 for non-existent lead."""
    res = client.get(
        "/leads/99999/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_opportunities_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/leads/1/opportunities")
    assert res.status_code == 401


def test_opportunities_response_fields(client, admin_headers, operator_a_headers):
    """Response contains all required fields."""
    company = _create_company(client, admin_headers, name="OppFieldsCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_opportunity(
        client, operator_a_headers, company["id"],
        title="Fields Opp", lead_id=lead["id"],
    )

    res = client.get(
        f"/leads/{lead['id']}/opportunities",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    item = res.json()["opportunities"][0]
    assert "opportunity_id" in item
    assert "title" in item
    assert "source" in item
    assert "next_action" in item
    assert "outcome" in item
    assert "budget" in item
    assert "deadline" in item
    assert "created_at" in item
