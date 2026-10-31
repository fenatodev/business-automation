"""WP-188 — Brief related conversations.

Tests that the operator can view conversations related to a brief's
opportunity, with tenant isolation and proper validation.
"""
from datetime import datetime, timezone


class TestBriefConversations:
    """Test GET /proposal-briefs/{id}/conversations."""

    def _create_company(self, client, headers, name="Company"):
        resp = client.post("/companies", json={"name": name, "slug": name.lower()}, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_opportunity(self, client, company_id, headers, title="Opp"):
        resp = client.post("/opportunities", json={
            "company_id": company_id,
            "source": "manual",
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_brief(self, client, headers, opportunity_id):
        resp = client.patch(
            f"/opportunities/{opportunity_id}/triage",
            headers=headers,
            json={"next_action": "prepare_proposal"},
        )
        assert resp.status_code == 200
        resp = client.post(
            f"/opportunities/{opportunity_id}/proposal-brief",
            headers=headers,
            json={
                "offer_reference": f"OFF-{opportunity_id}",
                "diagnosis": "Diagnosis",
                "scope": "Scope",
                "deliverables": "Deliverables",
                "acceptance_criteria": "Acceptance",
            },
        )
        assert resp.status_code == 200
        return resp.json()

    def _create_lead(self, client, company_id, headers, name="Lead"):
        resp = client.post("/leads", json={
            "company_id": company_id,
            "name": name,
            "phone": "5511999999999",
            "source": "manual",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_conversation(self, client, company_id, lead_id, headers, channel="whatsapp"):
        resp = client.post("/conversations", json={
            "company_id": company_id,
            "channel": channel,
            "lead_id": lead_id,
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_get_brief_conversations(self, client, admin_headers, operator_a_headers):
        """Get conversations for a brief's opportunity."""
        company = self._create_company(client, admin_headers, "ConvCo")
        opp = self._create_opportunity(client, company["id"], operator_a_headers, "Test")
        brief = self._create_brief(client, operator_a_headers, opp["id"])
        lead = self._create_lead(client, company["id"], operator_a_headers, "ConvLead")
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        res = client.get(
            f"/proposal-briefs/{brief['id']}/conversations",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        convs = res.json()
        assert isinstance(convs, list)
        assert len(convs) >= 1

    def test_get_brief_conversations_empty(self, client, admin_headers, operator_a_headers):
        """Get conversations returns empty list when no conversations exist."""
        company = self._create_company(client, admin_headers, "EmptyCo")
        opp = self._create_opportunity(client, company["id"], operator_a_headers, "Test")
        brief = self._create_brief(client, operator_a_headers, opp["id"])

        res = client.get(
            f"/proposal-briefs/{brief['id']}/conversations",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        convs = res.json()
        assert isinstance(convs, list)
        assert len(convs) == 0

    def test_get_brief_conversations_not_found(self, client, operator_a_headers):
        """Non-existent brief returns 404."""
        res = client.get(
            "/proposal-briefs/99999/conversations",
            headers=operator_a_headers,
        )
        assert res.status_code == 404

    def test_get_brief_conversations_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot view conversations from another tenant."""
        company_a = self._create_company(client, admin_headers, "TenantACo")
        company_b = self._create_company(client, admin_headers, "TenantBCo")

        opp_b = self._create_opportunity(client, company_b["id"], operator_b_headers, "OppB")
        brief_b = self._create_brief(client, operator_b_headers, opp_b["id"])

        res = client.get(
            f"/proposal-briefs/{brief_b['id']}/conversations",
            headers=operator_a_headers,
        )
        assert res.status_code == 404

    def test_get_brief_conversations_requires_auth(self, client, admin_headers, operator_a_headers):
        """Requires authentication."""
        res = client.get("/proposal-briefs/1/conversations")
        assert res.status_code in (401, 403)
