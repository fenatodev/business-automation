"""WP-142 — Conversas relacionadas à oportunidade.

Testa o endpoint GET /opportunities/{id}/conversations que retorna
conversas da mesma company que a oportunidade, com tenant isolation.
"""
from datetime import datetime, timezone


class TestOpportunityConversations:
    """Test opportunity-related conversations endpoint."""

    def _create_company(self, client, headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_opportunity(self, client, company_id, headers):
        resp = client.post("/opportunities", json={
            "company_id": company_id,
            "source": "manual",
            "external_url": "https://example.com/opp",
            "title": "Test Opportunity",
            "description": "Test description",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_conversation(self, client, company_id, headers, lead_id=None):
        data = {
            "company_id": company_id,
            "channel": "whatsapp",
        }
        if lead_id:
            data["lead_id"] = lead_id
        resp = client.post("/conversations", json=data, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_lead(self, client, company_id, headers):
        resp = client.post("/leads", json={
            "company_id": company_id,
            "name": "Test Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_get_conversations_returns_empty_list(self, client, admin_headers, operator_a_headers):
        """GET /opportunities/{id}/conversations returns empty list when no conversations exist."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/conversations",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_conversations_returns_company_conversations(self, client, admin_headers, operator_a_headers):
        """Endpoint returns conversations belonging to the same company."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], operator_a_headers, lead["id"])

        resp = client.get(
            f"/opportunities/{opp['id']}/conversations",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        conversations = resp.json()
        assert len(conversations) >= 1

    def test_get_conversations_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A sees only their company's conversations, not company B's."""
        # operator_a is bound to company_id=1
        company_a = self._create_company(client, admin_headers)
        assert company_a["id"] == 1
        opp_a = self._create_opportunity(client, company_a["id"], operator_a_headers)

        # Create conversation for company A
        lead_a = self._create_lead(client, company_a["id"], operator_a_headers)
        self._create_conversation(client, company_a["id"], operator_a_headers, lead_a["id"])

        # Create company B and conversation
        company_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b",
        }, headers=admin_headers).json()
        lead_b = self._create_lead(client, company_b["id"], operator_b_headers)
        self._create_conversation(client, company_b["id"], operator_b_headers, lead_b["id"])

        # Operator A should only see conversations from company A
        resp = client.get(
            f"/opportunities/{opp_a['id']}/conversations",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        # Should not include conversations from company B
        for conv in resp.json():
            assert conv["company_id"] == company_a["id"]

    def test_get_conversations_requires_auth(self, client, admin_headers, operator_a_headers):
        """Endpoint requires authentication."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(f"/opportunities/{opp['id']}/conversations")
        assert resp.status_code in (401, 403)

    def test_get_conversations_404_for_unknown_opportunity(self, client, admin_headers, operator_a_headers):
        """Returns 404 when opportunity doesn't exist."""
        company = self._create_company(client, admin_headers)
        # Create a conversation so the company has data
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], operator_a_headers, lead["id"])

        resp = client.get(
            "/opportunities/99999/conversations",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404

    def test_get_conversations_404_for_other_tenant_opportunity(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Returns 404 when opportunity belongs to another tenant."""
        # operator_a is bound to company_id=1, operator_b to company_id=2
        company_a = self._create_company(client, admin_headers)
        company_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b-2",
        }, headers=admin_headers).json()
        # operator_b creates opportunity on company B (company_id=2)
        opp_b = self._create_opportunity(client, company_b["id"], operator_b_headers)

        # Operator A (bound to company_id=1) cannot access opportunity from company B
        resp = client.get(
            f"/opportunities/{opp_b['id']}/conversations",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404

    def test_conversations_ordered_by_id_desc(self, client, admin_headers, operator_a_headers):
        """Conversations are returned ordered by ID descending."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)

        # Create multiple conversations
        conv1 = self._create_conversation(client, company["id"], operator_a_headers, lead["id"])
        conv2 = self._create_conversation(client, company["id"], operator_a_headers, lead["id"])
        assert conv2["id"] > conv1["id"]

        resp = client.get(
            f"/opportunities/{opp['id']}/conversations",
            headers=operator_a_headers,
        )
        conversations = resp.json()
        ids = [c["id"] for c in conversations]
        assert ids == sorted(ids, reverse=True)

    def test_conversations_limited_to_50(self, client, admin_headers, operator_a_headers):
        """Endpoint limits results to 50 conversations."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)

        # Create more than 50 conversations
        for _ in range(55):
            self._create_conversation(client, company["id"], operator_a_headers, lead["id"])

        resp = client.get(
            f"/opportunities/{opp['id']}/conversations",
            headers=operator_a_headers,
        )
        conversations = resp.json()
        assert len(conversations) == 50
