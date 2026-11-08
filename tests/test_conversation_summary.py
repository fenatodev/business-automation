"""WP-516 — Conversation summary endpoint with graceful fallback."""
from datetime import datetime, timezone
from unittest.mock import patch

from app.services.agent import AgentServiceError


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Lead"):
    res = client.post(
        "/leads",
        headers=headers,
        json={"company_id": company_id, "name": name, "phone": "5511999999999", "source": "manual"},
    )
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, headers, company_id, lead_id=None, channel="whatsapp"):
    data = {"channel": channel, "company_id": company_id}
    if lead_id is not None:
        data["lead_id"] = lead_id
    res = client.post(
        "/conversations",
        headers=headers,
        json=data,
    )
    assert res.status_code == 200
    return res.json()


def _add_message(client, headers, conversation_id, sender_type="customer", content="Hello"):
    res = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={"sender_type": sender_type, "content": content},
    )
    assert res.status_code == 200
    return res.json()


# --- Summary with empty conversation ---


def test_summarize_empty_conversation(client, admin_headers, operator_a_headers):
    """Summarize an empty conversation returns a default message."""
    company = _create_company(client, admin_headers, name="EmptyConvCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="EmptyLead")
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    res = client.post(
        f"/conversations/{conv['id']}/summarize",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "Nenhuma mensagem" in data["summary"]
    assert data["key_points"] == []
    assert data["action_items"] == []


# --- Summary with agent failure (graceful fallback) ---


def test_summarize_agent_failure_fallback(client, admin_headers, operator_a_headers):
    """When agent fails, return fallback summary from last message."""
    company = _create_company(client, admin_headers, name="FallbackCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="FallbackLead")
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])
    _add_message(client, operator_a_headers, conv["id"], "customer", "Preciso de um site novo")

    with patch("app.services.agent.httpx.post") as mock_post:
        mock_post.side_effect = AgentServiceError("Ollama request failed")

        res = client.post(
            f"/conversations/{conv['id']}/summarize",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "Última mensagem" in data["summary"]
        assert "Preciso de um site novo" in data["summary"]
        assert data["key_points"] == []
        assert data["action_items"] == []


def test_summarize_agent_failure_long_message(client, admin_headers, operator_a_headers):
    """Fallback summary truncates long messages."""
    company = _create_company(client, admin_headers, name="TruncateCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="TruncateLead")
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])
    long_msg = "A" * 300
    _add_message(client, operator_a_headers, conv["id"], "customer", long_msg)

    with patch("app.services.agent.httpx.post") as mock_post:
        mock_post.side_effect = AgentServiceError("Ollama request failed")

        res = client.post(
            f"/conversations/{conv['id']}/summarize",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "..." in data["summary"]
        assert len(data["summary"]) < len(long_msg) + 20


# --- Summary with successful agent response ---


def test_summarize_agent_success(client, admin_headers, operator_a_headers):
    """When agent succeeds, return the summary result."""
    company = _create_company(client, admin_headers, name="SuccessCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="SuccessLead")
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])
    _add_message(client, operator_a_headers, conv["id"], "customer", "Olá, preciso de ajuda")

    mock_response = {
        "summary": "Cliente precisa de ajuda",
        "key_points": ["Cliente solicitou ajuda"],
        "action_items": ["Responder ao cliente"],
    }

    with patch("app.services.agent.httpx.post") as mock_post:
        mock_post.return_value = type("MockResp", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"message": {"content": '{"summary": "Cliente precisa de ajuda", "key_points": ["Cliente solicitou ajuda"], "action_items": ["Responder ao cliente"]}'}}
        })()

        res = client.post(
            f"/conversations/{conv['id']}/summarize",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"] == "Cliente precisa de ajuda"
        assert "Cliente solicitou ajuda" in data["key_points"]
        assert "Responder ao cliente" in data["action_items"]


def test_summarize_agent_non_json_response(client, admin_headers, operator_a_headers):
    """When agent returns non-JSON, use raw content as summary."""
    company = _create_company(client, admin_headers, name="NonJsonCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="NonJsonLead")
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])
    _add_message(client, operator_a_headers, conv["id"], "customer", "Teste")

    with patch("app.services.agent.httpx.post") as mock_post:
        mock_post.return_value = type("MockResp", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"message": {"content": "Resumo em texto puro sem JSON"}}
        })()

        res = client.post(
            f"/conversations/{conv['id']}/summarize",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"] == "Resumo em texto puro sem JSON"
        assert data["key_points"] == []
        assert data["action_items"] == []


# --- Tenant isolation ---


def test_summarize_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot summarize Operator B's conversation."""
    _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")
    lead_b = _create_lead(client, operator_b_headers, company_b["id"], name="IsoBLead")
    conv_b = _create_conversation(client, operator_b_headers, company_b["id"], lead_id=lead_b["id"])
    _add_message(client, operator_b_headers, conv_b["id"], "customer", "Secret")

    res = client.post(
        f"/conversations/{conv_b['id']}/summarize",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


# --- Auth ---


def test_summarize_requires_auth(client):
    """Summarize endpoint requires authentication."""
    res = client.post("/conversations/999/summarize")
    assert res.status_code in (401, 403)


# --- Not found ---


def test_summarize_not_found(client, operator_a_headers):
    """Summarize non-existent conversation returns 404."""
    res = client.post(
        "/conversations/99999/summarize",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
