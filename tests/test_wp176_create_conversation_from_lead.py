"""WP-176 — Create conversation from lead detail panel.

Tests that the operator UI can create a new conversation linked to a lead
from the lead detail panel, following the same pattern as WP-089
(create conversation from customer).
"""
import pytest


@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "web", "telegram", "email"])
def test_create_conversation_from_lead_channel(client, admin_headers, operator_a_headers, channel):
    """Creating a conversation from a lead works for all allowed channels."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "Co-" + channel, "slug": "co-" + channel,
    }).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "Lead " + channel,
        "phone": "5511999990000",
        "source": "manual",
    }).json()

    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": channel,
        "lead_id": lead["id"],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["channel"] == channel
    assert data["lead_id"] == lead["id"]
    assert data["customer_id"] is None
    assert data["status"] == "open"


def test_create_conversation_from_lead_requires_auth(client, admin_headers, operator_a_headers):
    """Creating a conversation from a lead requires authentication."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "AuthCo", "slug": "authco",
    }).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "AuthLead",
        "phone": "5511999990001",
        "source": "manual",
    }).json()

    res = client.post("/conversations", json={
        "company_id": company["id"],
        "channel": "whatsapp",
        "lead_id": lead["id"],
    })
    assert res.status_code in (401, 403)


def test_create_conversation_from_lead_tenant_isolation(client, admin_headers, operator_a_headers):
    """A lead from another company cannot be used to create a conversation."""
    company_a = client.post("/companies", headers=admin_headers, json={
        "name": "TenantA", "slug": "tenanta",
    }).json()
    # Create a lead in company A, then try to create a conversation
    # with a different company_id — should be rejected
    lead_a = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company_a["id"],
        "name": "LeadA",
        "phone": "5511999990002",
        "source": "manual",
    }).json()

    # Try to create a conversation with a mismatched company_id
    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": 99999,
        "channel": "whatsapp",
        "lead_id": lead_a["id"],
    })
    # The backend validates company_id match first
    assert res.status_code in (400, 403, 404)


def test_create_conversation_from_lead_invalid_channel(client, admin_headers, operator_a_headers):
    """Creating a conversation with an invalid channel is rejected."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "InvalidCo", "slug": "invalidco",
    }).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "InvalidLead",
        "phone": "5511999990003",
        "source": "manual",
    }).json()

    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": "sms",
        "lead_id": lead["id"],
    })
    assert res.status_code in (400, 422)


def test_create_conversation_from_lead_nonexistent(client, admin_headers, operator_a_headers):
    """Creating a conversation with a nonexistent lead is rejected."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "NonexistCo", "slug": "nonexistco",
    }).json()

    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": "whatsapp",
        "lead_id": 99999,
    })
    assert res.status_code == 404


def test_create_conversation_from_lead_no_lead_no_customer(client, admin_headers, operator_a_headers):
    """Creating a conversation without lead_id or customer_id is rejected."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "NoLinkCo", "slug": "nolinkco",
    }).json()

    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": "whatsapp",
    })
    assert res.status_code == 400


def test_create_conversation_from_lead_both_lead_and_customer(client, admin_headers, operator_a_headers):
    """Creating a conversation with both lead_id and customer_id is rejected."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "BothCo", "slug": "bothco",
    }).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "BothLead",
        "phone": "5511999990004",
        "source": "manual",
    }).json()
    customer = client.post("/customers", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "BothCustomer",
        "phone": "5511999990005",
    }).json()

    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": "whatsapp",
        "lead_id": lead["id"],
        "customer_id": customer["id"],
    })
    assert res.status_code == 400


def test_create_conversation_from_lead_creates_open_status(client, admin_headers, operator_a_headers):
    """A conversation created from a lead starts with 'open' status."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "OpenCo", "slug": "openco",
    }).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "OpenLead",
        "phone": "5511999990006",
        "source": "manual",
    }).json()

    res = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": "web",
        "lead_id": lead["id"],
    })
    assert res.status_code == 200
    assert res.json()["status"] == "open"


def test_create_conversation_from_lead_visible_in_list(client, admin_headers, operator_a_headers):
    """A conversation created from a lead appears in the conversations list."""
    company = client.post("/companies", headers=admin_headers, json={
        "name": "ListCo", "slug": "listco",
    }).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"],
        "name": "ListLead",
        "phone": "5511999990007",
        "source": "manual",
    }).json()

    conv = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"],
        "channel": "telegram",
        "lead_id": lead["id"],
    }).json()

    res = client.get(
        f"/companies/{company['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    convs = res.json()
    assert any(c["id"] == conv["id"] for c in convs)
    matching = [c for c in convs if c["id"] == conv["id"]]
    assert matching[0]["lead_id"] == lead["id"]


def test_create_conversation_from_lead_ui_button_exists():
    """The lead detail panel has a 'Nova conversa' button."""
    from pathlib import Path
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="lead-new-conv"' in html
    assert "Nova conversa" in html


def test_create_conversation_from_lead_ui_handler_exists():
    """The app.js has a handler for lead-new-conv button."""
    from pathlib import Path
    js = Path("app/operator_ui/app.js").read_text()
    assert 'lead-new-conv' in js
    assert "createConversationFromLead" in js


def test_create_conversation_from_lead_ui_uses_post():
    """The createConversationFromLead function uses POST /conversations."""
    from pathlib import Path
    js = Path("app/operator_ui/app.js").read_text()
    # Find the function body
    idx = js.find("createConversationFromLead")
    func_body = js[idx:idx + 1000]
    assert '"/conversations"' in func_body or "'/conversations'" in func_body
    assert 'method: "POST"' in func_body or "method:\"POST\"" in func_body
    assert "lead_id" in func_body
