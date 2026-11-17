"""Conversation analytics endpoint tests.

Tests the GET /conversations/analytics endpoint that returns
conversation metrics for the operator dashboard.
"""
from conftest import TestingSessionLocal


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Test Lead"):
    res = client.post(
        "/leads",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": "+5511999999999",
            "source": "manual",
        },
    )
    assert res.status_code == 200, f"Failed to create lead: {res.text}"
    return res.json()


def _create_conversation(client, headers, company_id, channel="whatsapp", lead=None):
    """Create a conversation. If lead is None, creates one automatically."""
    if lead is None:
        lead = _create_lead(client, headers, company_id)
    payload = {
        "company_id": company_id,
        "channel": channel,
        "lead_id": lead["id"],
    }
    res = client.post(
        "/conversations",
        headers=headers,
        json=payload,
    )
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


def _close_conversation(client, headers, conversation_id):
    res = client.patch(
        f"/conversations/{conversation_id}",
        headers=headers,
        json={"status": "closed"},
    )
    assert res.status_code == 200
    return res.json()


def test_analytics_empty_when_no_conversations(
    client, admin_headers, operator_a_headers
):
    """Returns zeros when no conversations exist."""
    _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        "/conversations/analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_conversations"] == 0
    assert data["open_conversations"] == 0
    assert data["closed_conversations"] == 0
    assert data["by_channel"] == []
    assert data["total_messages"] == 0
    assert data["customer_messages"] == 0
    assert data["agent_messages"] == 0


def test_analytics_counts_conversations_by_status(
    client, admin_headers, operator_a_headers
):
    """Correctly counts open and closed conversations."""
    company = _create_company(client, admin_headers, name="StatusCo")

    c1 = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    c2 = _create_conversation(client, operator_a_headers, company["id"], channel="email")
    c3 = _create_conversation(client, operator_a_headers, company["id"], channel="web")
    _close_conversation(client, operator_a_headers, c2["id"])
    _close_conversation(client, operator_a_headers, c3["id"])

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_conversations"] == 3
    assert data["open_conversations"] == 1
    assert data["closed_conversations"] == 2


def test_analytics_counts_by_channel(
    client, admin_headers, operator_a_headers
):
    """Correctly groups conversations by channel."""
    company = _create_company(client, admin_headers, name="ChannelCo")

    _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    _create_conversation(client, operator_a_headers, company["id"], channel="email")
    _create_conversation(client, operator_a_headers, company["id"], channel="web")

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    data = res.json()

    channels = {c["channel"]: c["count"] for c in data["by_channel"]}
    assert channels["whatsapp"] == 2
    assert channels["email"] == 1
    assert channels["web"] == 1


def test_analytics_counts_messages_by_sender_type(
    client, admin_headers, operator_a_headers
):
    """Correctly counts messages by sender type."""
    company = _create_company(client, admin_headers, name="MsgCo")
    conv = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")

    _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Hi")
    _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="How much?")
    _create_message(client, operator_a_headers, conv["id"], sender_type="agent", content="Hello!")

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    data = res.json()
    assert data["total_messages"] == 3
    assert data["customer_messages"] == 2
    assert data["agent_messages"] == 1


def test_analytics_tenant_isolation(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Only returns analytics for the authenticated tenant."""
    company_a = _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")

    for i in range(3):
        _create_conversation(client, operator_a_headers, company_a["id"], channel="whatsapp")
    for i in range(5):
        _create_conversation(client, operator_b_headers, company_b["id"], channel="email")

    res_a = client.get("/conversations/analytics", headers=operator_a_headers)
    data_a = res_a.json()
    assert data_a["total_conversations"] == 3

    res_b = client.get("/conversations/analytics", headers=operator_b_headers)
    data_b = res_b.json()
    assert data_b["total_conversations"] == 5


def test_analytics_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/conversations/analytics")
    assert res.status_code in (401, 403)


def test_analytics_response_fields(
    client, admin_headers, operator_a_headers
):
    """Response includes all expected fields with correct types."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    conv = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Hi")

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert "total_conversations" in data
    assert "open_conversations" in data
    assert "closed_conversations" in data
    assert "by_channel" in data
    assert "total_messages" in data
    assert "customer_messages" in data
    assert "agent_messages" in data

    assert isinstance(data["total_conversations"], int)
    assert isinstance(data["open_conversations"], int)
    assert isinstance(data["closed_conversations"], int)
    assert isinstance(data["by_channel"], list)
    assert isinstance(data["total_messages"], int)
    assert isinstance(data["customer_messages"], int)
    assert isinstance(data["agent_messages"], int)

    for channel in data["by_channel"]:
        assert "channel" in channel
        assert "count" in channel
        assert isinstance(channel["channel"], str)
        assert isinstance(channel["count"], int)


def test_analytics_messages_only_from_tenant_conversations(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Message counts only include messages from tenant's conversations."""
    company_a = _create_company(client, admin_headers, name="MsgIsoA")
    company_b = _create_company(client, admin_headers, name="MsgIsoB")

    lead_a = _create_lead(client, operator_a_headers, company_a["id"], name="Lead A")
    lead_b = _create_lead(client, operator_b_headers, company_b["id"], name="Lead B")

    conv_a = _create_conversation(client, operator_a_headers, company_a["id"], channel="whatsapp", lead=lead_a)
    conv_b = _create_conversation(client, operator_b_headers, company_b["id"], channel="email", lead=lead_b)

    for i in range(5):
        _create_message(client, operator_b_headers, conv_b["id"], sender_type="customer", content=f"B msg {i}")
    _create_message(client, operator_a_headers, conv_a["id"], sender_type="customer", content="A msg")

    res_a = client.get("/conversations/analytics", headers=operator_a_headers)
    data_a = res_a.json()
    assert data_a["total_messages"] == 1
    assert data_a["customer_messages"] == 1

    res_b = client.get("/conversations/analytics", headers=operator_b_headers)
    data_b = res_b.json()
    assert data_b["total_messages"] == 5
    assert data_b["customer_messages"] == 5


def test_analytics_multiple_channels(
    client, admin_headers, operator_a_headers
):
    """Handles multiple channels correctly."""
    company = _create_company(client, admin_headers, name="MultiChCo")

    channels = ["whatsapp", "email", "web", "instagram", "telegram"]
    for ch in channels:
        _create_conversation(client, operator_a_headers, company["id"], channel=ch)

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    data = res.json()

    channel_names = {c["channel"] for c in data["by_channel"]}
    assert channel_names == set(channels)
    assert data["total_conversations"] == 5


def test_analytics_closed_conversations_still_counted(
    client, admin_headers, operator_a_headers
):
    """Closed conversations are included in total and channel counts."""
    company = _create_company(client, admin_headers, name="ClosedCo")

    c1 = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    c2 = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    _close_conversation(client, operator_a_headers, c1["id"])

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    data = res.json()
    assert data["total_conversations"] == 2

    channels = {c["channel"]: c["count"] for c in data["by_channel"]}
    assert channels["whatsapp"] == 2


def test_analytics_agent_and_customer_messages(
    client, admin_headers, operator_a_headers
):
    """Correctly separates agent and customer messages."""
    company = _create_company(client, admin_headers, name="AgentMsgCo")
    conv = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")

    _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Customer 1")
    _create_message(client, operator_a_headers, conv["id"], sender_type="agent", content="Agent 1")
    _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Customer 2")
    _create_message(client, operator_a_headers, conv["id"], sender_type="agent", content="Agent 2")
    _create_message(client, operator_a_headers, conv["id"], sender_type="agent", content="Agent 3")

    res = client.get("/conversations/analytics", headers=operator_a_headers)
    data = res.json()
    assert data["total_messages"] == 5
    assert data["customer_messages"] == 2
    assert data["agent_messages"] == 3
