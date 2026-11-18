"""Customer conversations endpoint tests.

Tests GET /customers/{customer_id}/conversations that returns all
conversations linked to a customer.
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


def _create_conversation_for_customer(client, headers, company_id, customer_id, channel="whatsapp"):
    payload = {
        "company_id": company_id,
        "channel": channel,
        "customer_id": customer_id,
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


def test_empty_when_no_conversations(client, admin_headers, operator_a_headers):
    """Returns empty when customer has no conversations."""
    company = _create_company(client, admin_headers, name="EmptyCo")
    customer = _create_customer(client, operator_a_headers, company["id"])

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["conversations"] == []


def test_returns_linked_conversations(client, admin_headers, operator_a_headers):
    """Returns conversations linked to the customer."""
    company = _create_company(client, admin_headers, name="ConvCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    conv = _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"]
    )

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["conversations"][0]["conversation_id"] == conv["id"]
    assert data["conversations"][0]["channel"] == "whatsapp"


def test_includes_message_count(client, admin_headers, operator_a_headers):
    """Conversation includes message count."""
    company = _create_company(client, admin_headers, name="MsgCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    conv = _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"]
    )
    _create_message(client, operator_a_headers, conv["id"], "customer", "Hi")
    _create_message(client, operator_a_headers, conv["id"], "agent", "Hello")

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["conversations"][0]["message_count"] == 2


def test_multiple_channels(client, admin_headers, operator_a_headers):
    """Works across different channels."""
    company = _create_company(client, admin_headers, name="MultiChCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"], "whatsapp"
    )
    _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"], "email"
    )

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    channels = {c["channel"] for c in data["conversations"]}
    assert "whatsapp" in channels
    assert "email" in channels


def test_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Conversations are isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    customer_b = _create_customer(client, operator_b_headers, 2)
    _create_conversation_for_customer(
        client, operator_b_headers, 2, customer_b["id"]
    )

    res_a = client.get(
        f"/customers/{customer_b['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res_a.status_code == 404


def test_404_when_customer_not_found(client, operator_a_headers):
    """Returns 404 for non-existent customer."""
    res = client.get(
        "/customers/99999/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/customers/1/conversations")
    assert res.status_code == 401


def test_response_fields(client, admin_headers, operator_a_headers):
    """Response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    conv = _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"]
    )

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    item = res.json()["conversations"][0]
    assert "conversation_id" in item
    assert "channel" in item
    assert "status" in item
    assert "message_count" in item
    assert "created_at" in item


def test_sorted_by_id(client, admin_headers, operator_a_headers):
    """Conversations are sorted by ID ascending."""
    company = _create_company(client, admin_headers, name="SortCo")
    customer = _create_customer(client, operator_a_headers, company["id"])

    conv1 = _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"]
    )
    conv2 = _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"]
    )

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    ids = [c["conversation_id"] for c in data["conversations"]]
    assert ids == sorted(ids)


def test_includes_status(client, admin_headers, operator_a_headers):
    """Response includes conversation status."""
    company = _create_company(client, admin_headers, name="StatusCo")
    customer = _create_customer(client, operator_a_headers, company["id"])
    conv = _create_conversation_for_customer(
        client, operator_a_headers, company["id"], customer["id"]
    )

    # Close the conversation
    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 200

    res = client.get(
        f"/customers/{customer['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["conversations"][0]["status"] == "closed"
