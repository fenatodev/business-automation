"""WP-180 — Bulk delete for opportunities and conversations.

Tests that the operator can bulk delete opportunities and conversations
with tenant isolation, following the same pattern as leads/customers.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp"):
    res = client.post("/opportunities", headers=headers, json={
        "source": "manual",
        "external_url": f"https://example.com/{title}",
        "title": title,
        "description": "Test",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    })
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, headers, channel="whatsapp"):
    # Get company_id from an existing opportunity
    res = client.get("/opportunities", headers=headers)
    if res.status_code == 200 and res.json():
        company_id = res.json()[0]["company_id"]
    else:
        # Fallback: create a company first
        company_id = None
    res = client.post("/conversations", headers=headers, json={
        "company_id": company_id,
        "channel": channel,
    })
    assert res.status_code == 200, f"Conversation creation failed: {res.text}"
    return res.json()


class TestBulkDeleteOpportunities:
    """Test POST /opportunities/bulk-delete."""

    def test_bulk_delete_opportunities(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="BulkOpp")
        opp1 = _create_opportunity(client, operator_a_headers, title="Del1")
        opp2 = _create_opportunity(client, operator_a_headers, title="Del2")

        res = client.post("/opportunities/bulk-delete", headers=operator_a_headers, json={
            "opportunity_ids": [opp1["id"], opp2["id"]],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] == 2
        assert sorted(data["deleted_ids"]) == sorted([opp1["id"], opp2["id"]])
        assert data["skipped"] == []

    def test_bulk_delete_opportunities_tenant_isolation(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="TenantOpp")
        opp = _create_opportunity(client, operator_a_headers, title="Mine")

        res = client.post("/opportunities/bulk-delete", headers=operator_a_headers, json={
            "opportunity_ids": [99999, opp["id"]],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] == 1
        assert data["deleted_ids"] == [opp["id"]]
        assert 99999 in data["skipped"]

    def test_bulk_delete_opportunities_requires_auth(self, client, admin_headers, operator_a_headers):
        res = client.post("/opportunities/bulk-delete", json={"opportunity_ids": [1]})
        assert res.status_code in (401, 403)

    def test_bulk_delete_opportunities_empty_list_rejected(self, client, admin_headers, operator_a_headers):
        res = client.post("/opportunities/bulk-delete", headers=operator_a_headers, json={
            "opportunity_ids": [],
        })
        assert res.status_code in (400, 422)


class TestBulkDeleteConversations:
    """Test POST /conversations/bulk-delete."""

    def test_bulk_delete_conversations(self, client, admin_headers, operator_a_headers):
        company = _create_company(client, admin_headers, name="BulkConv")
        lead = client.post("/leads", headers=operator_a_headers, json={
            "company_id": company["id"], "name": "Lead", "phone": "5511999990000", "source": "manual",
        }).json()
        conv1 = client.post("/conversations", headers=operator_a_headers, json={
            "company_id": company["id"], "channel": "whatsapp", "lead_id": lead["id"],
        }).json()
        conv2 = client.post("/conversations", headers=operator_a_headers, json={
            "company_id": company["id"], "channel": "email", "lead_id": lead["id"],
        }).json()

        res = client.post("/conversations/bulk-delete", headers=operator_a_headers, json={
            "conversation_ids": [conv1["id"], conv2["id"]],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] == 2
        assert sorted(data["deleted_ids"]) == sorted([conv1["id"], conv2["id"]])
        assert data["skipped"] == []

    def test_bulk_delete_conversations_tenant_isolation(self, client, admin_headers, operator_a_headers):
        company = _create_company(client, admin_headers, name="TenantConv")
        lead = client.post("/leads", headers=operator_a_headers, json={
            "company_id": company["id"], "name": "Lead", "phone": "5511999990001", "source": "manual",
        }).json()
        conv = client.post("/conversations", headers=operator_a_headers, json={
            "company_id": company["id"], "channel": "web", "lead_id": lead["id"],
        }).json()

        res = client.post("/conversations/bulk-delete", headers=operator_a_headers, json={
            "conversation_ids": [99999, conv["id"]],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] == 1
        assert data["deleted_ids"] == [conv["id"]]
        assert 99999 in data["skipped"]

    def test_bulk_delete_conversations_requires_auth(self, client, admin_headers, operator_a_headers):
        res = client.post("/conversations/bulk-delete", json={"conversation_ids": [1]})
        assert res.status_code in (401, 403)

    def test_bulk_delete_conversations_empty_list_rejected(self, client, admin_headers, operator_a_headers):
        res = client.post("/conversations/bulk-delete", headers=operator_a_headers, json={
            "conversation_ids": [],
        })
        assert res.status_code in (400, 422)
