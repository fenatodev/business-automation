"""WP-543 — Auto-triage based on content tests."""
from app.services.agent import (
    AgentProvider,
    NoopProvider,
    OllamaProvider,
    _available_providers,
    get_provider,
    register_provider,
    suggest_triage,
)


def _reset_providers():
    _available_providers.clear()


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
    res = client.post("/conversations", headers=headers, json=data)
    assert res.status_code == 200
    return res.json()


def _add_message(client, headers, conversation_id, sender_type, content):
    res = client.post(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
        json={"sender_type": sender_type, "content": content},
    )
    assert res.status_code == 200
    return res.json()


# --- Provider tests ---


def test_noop_provider_suggest_triage():
    """NoopProvider returns placeholder triage."""
    provider = NoopProvider()
    result = provider.suggest_triage([])
    assert "next_action" in result
    assert "confidence" in result
    assert "reason" in result
    assert result["next_action"] == "follow_up"
    assert result["confidence"] == 0.5


def test_noop_provider_suggest_triage_with_history():
    """NoopProvider accepts history without error."""
    provider = NoopProvider()
    history = [
        {"sender_type": "customer", "content": "Hello"},
        {"sender_type": "agent", "content": "Hi there"},
    ]
    result = provider.suggest_triage(history)
    assert "next_action" in result


def test_ollama_provider_suggest_triage_raises_on_failure():
    """OllamaProvider raises AgentServiceError on HTTP failure."""
    provider = OllamaProvider(base_url="http://localhost:99999")
    try:
        provider.suggest_triage([])
        assert False, "Expected AgentServiceError"
    except Exception as exc:
        # May be AgentServiceError or httpx.HTTPError
        assert "Ollama" in str(exc) or "failed" in str(exc).lower() or "99999" in str(exc)


def test_suggest_triage_uses_provider():
    """suggest_triage uses the registered provider."""
    _reset_providers()
    noop = NoopProvider()
    register_provider("default", noop)
    result = suggest_triage([])
    assert "next_action" in result
    assert "confidence" in result
    assert "reason" in result


def test_suggest_triage_provider_switching():
    """Switching providers changes triage behavior."""
    _reset_providers()
    noop = NoopProvider()
    register_provider("default", noop)

    result1 = suggest_triage([])
    assert result1["next_action"] == "follow_up"

    class CustomProvider(AgentProvider):
        def generate_reply(self, message, history, **kwargs):
            return "CUSTOM"
        def summarize(self, history, **kwargs):
            return {"summary": "CUSTOM", "key_points": [], "action_items": []}
        def health_check(self):
            return {"provider": "custom", "status": "healthy"}
        def suggest_triage(self, history):
            return {"next_action": "qualify", "confidence": 0.9, "reason": "Custom reason"}

    register_provider("default", CustomProvider())
    result2 = suggest_triage([])
    assert result2["next_action"] == "qualify"
    assert result2["confidence"] == 0.9


# --- Endpoint tests ---


def test_suggest_triage_endpoint(client, admin_headers, operator_a_headers):
    """POST /conversations/{id}/suggest-triage returns triage suggestion."""
    company = _create_company(client, admin_headers, name="TriageCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    _add_message(client, operator_a_headers, conv["id"], "customer", "Preciso de um orçamento")

    resp = client.post(
        f"/conversations/{conv['id']}/suggest-triage",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "next_action" in data
    assert "confidence" in data
    assert "reason" in data
    assert isinstance(data["confidence"], float)
    assert 0 <= data["confidence"] <= 1


def test_suggest_triage_endpoint_empty_conversation(client, admin_headers, operator_a_headers):
    """Triage works on empty conversation."""
    company = _create_company(client, admin_headers, name="EmptyCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    resp = client.post(
        f"/conversations/{conv['id']}/suggest-triage",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "next_action" in data


def test_suggest_triage_endpoint_not_found(client, operator_a_headers):
    """Triage returns 404 for unknown conversation."""
    resp = client.post(
        "/conversations/99999/suggest-triage",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_suggest_triage_endpoint_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot triage Operator B's conversation."""
    company_a = _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")
    lead_a = _create_lead(client, operator_a_headers, company_a["id"])
    conv_a = _create_conversation(client, operator_a_headers, company_a["id"], lead_id=lead_a["id"])

    # Operator B tries to triage Operator A's conversation
    resp = client.post(
        f"/conversations/{conv_a['id']}/suggest-triage",
        headers=operator_b_headers,
    )
    assert resp.status_code == 404


def test_suggest_triage_endpoint_requires_auth(client):
    """Triage requires authentication."""
    resp = client.post("/conversations/1/suggest-triage")
    assert resp.status_code in (401, 403)


def test_suggest_triage_response_fields(client, admin_headers, operator_a_headers):
    """Triage response has correct field types."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    resp = client.post(
        f"/conversations/{conv['id']}/suggest-triage",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["next_action"], str)
    assert isinstance(data["confidence"], (int, float))
    assert isinstance(data["reason"], str)
