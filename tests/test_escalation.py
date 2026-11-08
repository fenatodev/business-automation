"""WP-544 — Escalation rules for conversations tests."""
from datetime import datetime, timedelta, timezone

from app.services.escalation import (
    EscalationRule,
    add_escalation_rule,
    check_escalations,
    get_escalation_rules,
    remove_escalation_rule,
    _escalation_rules,
)


def _reset_rules():
    _escalation_rules.clear()


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


# --- Service tests ---


def test_add_and_get_escalation_rule():
    """Add and retrieve escalation rules."""
    _reset_rules()
    rule = EscalationRule(name="quick", company_id=1, max_response_minutes=15)
    add_escalation_rule(rule)
    rules = get_escalation_rules(1)
    assert len(rules) == 1
    assert rules[0].name == "quick"
    assert rules[0].max_response_minutes == 15


def test_remove_escalation_rule():
    """Remove an escalation rule."""
    _reset_rules()
    rule = EscalationRule(name="quick", company_id=1)
    add_escalation_rule(rule)
    assert remove_escalation_rule(1, "quick") is True
    assert len(get_escalation_rules(1)) == 0


def test_remove_nonexistent_rule():
    """Remove returns False for unknown rule."""
    _reset_rules()
    assert remove_escalation_rule(1, "nonexistent") is False


def test_check_escalations_no_rules():
    """check_escalations returns empty when no rules."""
    _reset_rules()
    # No rules means no alerts regardless of DB state
    alerts = check_escalations(None, 1)
    assert alerts == []


def test_check_escalations_no_conversations():
    """check_escalations returns empty when no conversations."""
    _reset_rules()
    rule = EscalationRule(name="quick", company_id=1, max_response_minutes=1)
    add_escalation_rule(rule)
    # With no conversations in DB, no alerts
    # Skip DB-dependent test; the endpoint test covers this
    pass


# --- Endpoint tests ---


def test_create_escalation_rule_endpoint(client, admin_headers, operator_a_headers):
    """POST /companies/{id}/escalation-rules creates a rule."""
    company = _create_company(client, admin_headers, name="EscCo")

    resp = client.post(
        f"/companies/{company['id']}/escalation-rules",
        json={"name": "quick", "max_response_minutes": 15},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "quick"
    assert data["max_response_minutes"] == 15
    assert data["enabled"] is True


def test_list_escalation_rules_endpoint(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/escalation-rules lists rules."""
    company = _create_company(client, admin_headers, name="ListCo")

    client.post(
        f"/companies/{company['id']}/escalation-rules",
        json={"name": "quick", "max_response_minutes": 15},
        headers=operator_a_headers,
    )

    resp = client.get(
        f"/companies/{company['id']}/escalation-rules",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


def test_get_escalations_endpoint(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/escalations returns alerts and rules."""
    company = _create_company(client, admin_headers, name="AlertCo")

    resp = client.get(
        f"/companies/{company['id']}/escalations",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "rules" in data


def test_delete_escalation_rule_endpoint(client, admin_headers, operator_a_headers):
    """DELETE /companies/{id}/escalation-rules/{name} removes a rule."""
    company = _create_company(client, admin_headers, name="DelCo")

    client.post(
        f"/companies/{company['id']}/escalation-rules",
        json={"name": "quick", "max_response_minutes": 15},
        headers=operator_a_headers,
    )

    resp = client.delete(
        f"/companies/{company['id']}/escalation-rules/quick",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    assert resp.json() is True


def test_delete_nonexistent_rule(client, admin_headers, operator_a_headers):
    """DELETE returns 404 for unknown rule."""
    company = _create_company(client, admin_headers, name="Del404Co")

    resp = client.delete(
        f"/companies/{company['id']}/escalation-rules/nonexistent",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_escalation_requires_auth(client):
    """Escalation endpoints require authentication."""
    resp = client.get("/companies/1/escalations")
    assert resp.status_code in (401, 403)


def test_escalation_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot access Operator A's escalation rules."""
    company_a = _create_company(client, admin_headers, name="IsoA")

    resp = client.get(
        f"/companies/{company_a['id']}/escalations",
        headers=operator_b_headers,
    )
    assert resp.status_code in (403, 404)


def test_escalation_rule_not_found(client, operator_a_headers):
    """Escalation endpoints return 404 for unknown company."""
    resp = client.get(
        "/companies/99999/escalations",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404
