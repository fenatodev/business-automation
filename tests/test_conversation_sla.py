"""Conversation SLA monitoring endpoint tests.

Tests the GET /conversations/sla endpoint that identifies open conversations
where the customer's last message has no agent reply yet.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Message as MessageModel
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
    if lead is None:
        lead = _create_lead(client, headers, company_id)
    payload = {
        "company_id": company_id,
        "channel": channel,
        "lead_id": lead["id"],
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


def _backdate_message(message_id, minutes_ago):
    """Backdate a message's created_at for SLA threshold testing."""
    with TestingSessionLocal() as db:
        m = db.scalar(select(MessageModel).where(MessageModel.id == message_id))
        if m:
            m.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
            db.commit()


def test_sla_empty_when_no_conversations(client, admin_headers, operator_a_headers):
    """Returns empty when no conversations exist."""
    _create_company(client, admin_headers, name="EmptyCo")
    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 0
    assert data["pending_replies"] == []


def test_sla_empty_when_no_customer_messages(client, admin_headers, operator_a_headers):
    """Returns empty when conversations have no customer messages."""
    company = _create_company(client, admin_headers, name="AgentOnlyCo")
    conv = _create_conversation(client, operator_a_headers, company["id"])
    _create_message(client, operator_a_headers, conv["id"], sender_type="agent", content="Hi there")

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total_pending"] == 0


def test_sla_returns_pending_customer_message(client, admin_headers, operator_a_headers):
    """Returns conversation when last message is from customer."""
    company = _create_company(client, admin_headers, name="PendingCo")
    conv = _create_conversation(client, operator_a_headers, company["id"])
    msg = _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Help me")
    _backdate_message(msg["id"], 60)

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 1
    assert data["pending_replies"][0]["conversation_id"] == conv["id"]
    assert data["pending_replies"][0]["channel"] == "whatsapp"
    assert data["pending_replies"][0]["minutes_waiting"] >= 60


def test_sla_excludes_conversation_with_agent_reply(client, admin_headers, operator_a_headers):
    """Excludes conversation when agent replied after customer message."""
    company = _create_company(client, admin_headers, name="RepliedCo")
    conv = _create_conversation(client, operator_a_headers, company["id"])
    _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Question")
    _create_message(client, operator_a_headers, conv["id"], sender_type="agent", content="Answer")

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total_pending"] == 0


def test_sla_respects_minutes_threshold(client, admin_headers, operator_a_headers):
    """Filters by minutes_threshold parameter."""
    company = _create_company(client, admin_headers, name="ThresholdCo")
    conv = _create_conversation(client, operator_a_headers, company["id"])
    msg = _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Hi")
    _backdate_message(msg["id"], 10)

    # Threshold 30 minutes — should exclude
    res = client.get("/conversations/sla?minutes_threshold=30", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total_pending"] == 0

    # Threshold 5 minutes — should include
    res = client.get("/conversations/sla?minutes_threshold=5", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total_pending"] == 1


def test_sla_excludes_closed_conversations(client, admin_headers, operator_a_headers):
    """Excludes closed conversations from SLA monitoring."""
    company = _create_company(client, admin_headers, name="ClosedCo")
    conv = _create_conversation(client, operator_a_headers, company["id"])
    msg = _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Help")
    _backdate_message(msg["id"], 60)

    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 200

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total_pending"] == 0


def test_sla_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """SLA data is isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    # Create pending conversation only for company 2 (operator_b)
    conv_b = _create_conversation(client, operator_b_headers, 2)
    msg_b = _create_message(client, operator_b_headers, conv_b["id"], sender_type="customer", content="Help B")
    _backdate_message(msg_b["id"], 60)

    # Operator A sees nothing
    res_a = client.get("/conversations/sla", headers=operator_a_headers)
    assert res_a.status_code == 200
    assert res_a.json()["total_pending"] == 0

    # Operator B sees their own
    res_b = client.get("/conversations/sla", headers=operator_b_headers)
    assert res_b.status_code == 200
    assert res_b.json()["total_pending"] == 1


def test_sla_includes_lead_name(client, admin_headers, operator_a_headers):
    """SLA response includes lead name when available."""
    company = _create_company(client, admin_headers, name="LeadNameCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="João Silva")
    conv = _create_conversation(client, operator_a_headers, company["id"], lead=lead)
    msg = _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Olá")
    _backdate_message(msg["id"], 45)

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 1
    assert data["pending_replies"][0]["lead_name"] == "João Silva"


def test_sla_sorted_by_urgency(client, admin_headers, operator_a_headers):
    """Results are sorted by minutes_waiting descending (most urgent first)."""
    company = _create_company(client, admin_headers, name="UrgencyCo")

    conv1 = _create_conversation(client, operator_a_headers, company["id"])
    msg1 = _create_message(client, operator_a_headers, conv1["id"], sender_type="customer", content="Urgent 1")
    _backdate_message(msg1["id"], 20)

    conv2 = _create_conversation(client, operator_a_headers, company["id"])
    msg2 = _create_message(client, operator_a_headers, conv2["id"], sender_type="customer", content="Urgent 2")
    _backdate_message(msg2["id"], 90)

    res = client.get("/conversations/sla?minutes_threshold=5", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 2
    assert data["pending_replies"][0]["conversation_id"] == conv2["id"]
    assert data["pending_replies"][1]["conversation_id"] == conv1["id"]


def test_sla_validates_minutes_threshold_bounds(client, operator_a_headers):
    """Rejects invalid minutes_threshold values."""
    res = client.get("/conversations/sla?minutes_threshold=0", headers=operator_a_headers)
    assert res.status_code == 422

    res = client.get("/conversations/sla?minutes_threshold=1441", headers=operator_a_headers)
    assert res.status_code == 422


def test_sla_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/conversations/sla")
    assert res.status_code == 401


def test_sla_multiple_channels(client, admin_headers, operator_a_headers):
    """SLA works across different channels."""
    company = _create_company(client, admin_headers, name="MultiChannelCo")

    conv_wa = _create_conversation(client, operator_a_headers, company["id"], channel="whatsapp")
    msg_wa = _create_message(client, operator_a_headers, conv_wa["id"], sender_type="customer", content="WA msg")
    _backdate_message(msg_wa["id"], 45)

    conv_email = _create_conversation(client, operator_a_headers, company["id"], channel="email")
    msg_email = _create_message(client, operator_a_headers, conv_email["id"], sender_type="customer", content="Email msg")
    _backdate_message(msg_email["id"], 45)

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 2
    channels = {item["channel"] for item in data["pending_replies"]}
    assert "whatsapp" in channels
    assert "email" in channels


def test_sla_includes_customer_name(client, admin_headers, operator_a_headers):
    """SLA response includes customer name when conversation has customer_id."""
    company = _create_company(client, admin_headers, name="CustomerNameCo")

    res = client.post(
        "/customers",
        headers=operator_a_headers,
        json={"company_id": company["id"], "name": "Maria Santos", "phone": "+5511988888888"},
    )
    assert res.status_code == 200
    customer = res.json()

    payload = {
        "company_id": company["id"],
        "channel": "whatsapp",
        "customer_id": customer["id"],
    }
    res = client.post("/conversations", headers=operator_a_headers, json=payload)
    assert res.status_code == 200
    conv = res.json()

    msg = _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Preciso de ajuda")
    _backdate_message(msg["id"], 45)

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 1
    assert data["pending_replies"][0]["customer_name"] == "Maria Santos"


def test_sla_response_has_required_fields(client, admin_headers, operator_a_headers):
    """SLA response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    conv = _create_conversation(client, operator_a_headers, company["id"])
    msg = _create_message(client, operator_a_headers, conv["id"], sender_type="customer", content="Test")
    _backdate_message(msg["id"], 60)

    res = client.get("/conversations/sla", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert "pending_replies" in data
    assert "total_pending" in data

    item = data["pending_replies"][0]
    assert "conversation_id" in item
    assert "channel" in item
    assert "last_customer_message_at" in item
    assert "minutes_waiting" in item
    assert "lead_name" in item
    assert "customer_name" in item
