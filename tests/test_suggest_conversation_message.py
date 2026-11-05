"""WP-274: Test AI-assisted conversation message suggestion."""

import pytest
from unittest.mock import patch


class TestSuggestConversationMessage:
    """Verify suggest-message endpoint behavior."""

    def _setup_lead(self, client, admin_headers, operator_headers):
        """Create company and lead — return lead_id and company_id."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        cid = company.json()["id"]

        lead = client.post("/leads", headers=operator_headers, json={
            "company_id": cid, "name": "Test Lead", "phone": "5511999999999",
            "source": "manual", "interest": "Website redesign"
        })
        assert lead.status_code == 200
        return lead.json()["id"], cid

    def _setup_customer(self, client, admin_headers, operator_headers):
        """Create company and customer — return customer_id and company_id."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        cid = company.json()["id"]

        customer = client.post("/customers", headers=operator_headers, json={
            "company_id": cid, "name": "Test Customer", "phone": "5511999999999",
            "email": "customer@example.com"
        })
        assert customer.status_code == 200
        return customer.json()["id"], cid

    def test_suggest_from_lead_returns_message(self, client, admin_headers, operator_a_headers):
        """Suggest returns message suggestion from lead context."""
        lead_id, _ = self._setup_lead(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_message": "Olá, vi que tem interesse em redesign. Posso ajudar?", '
                '"reasoning": "Baseado no interesse do lead"}'
            )
            res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
                "company_id": 1, "channel": "whatsapp", "lead_id": lead_id
            })
        assert res.status_code == 200
        data = res.json()
        assert "suggested_message" in data
        assert "reasoning" in data

    def test_suggest_from_customer_returns_message(self, client, admin_headers, operator_a_headers):
        """Suggest returns message suggestion from customer context."""
        customer_id, _ = self._setup_customer(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_message": "Olá, gostaria de atualizá-lo sobre nossos serviços.", '
                '"reasoning": "Customer existente"}'
            )
            res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
                "company_id": 1, "channel": "email", "customer_id": customer_id
            })
        assert res.status_code == 200
        data = res.json()
        assert "suggested_message" in data

    def test_suggest_requires_lead_or_customer(self, client, admin_headers, operator_a_headers):
        """Returns 400 when neither lead_id nor customer_id is provided."""
        res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
            "company_id": 1, "channel": "whatsapp"
        })
        assert res.status_code == 400

    def test_suggest_404_lead_not_found(self, client, admin_headers, operator_a_headers):
        """Returns 404 for non-existent lead."""
        res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
            "company_id": 1, "channel": "whatsapp", "lead_id": 99999
        })
        assert res.status_code == 404

    def test_suggest_404_customer_not_found(self, client, admin_headers, operator_a_headers):
        """Returns 404 for non-existent customer."""
        res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
            "company_id": 1, "channel": "whatsapp", "customer_id": 99999
        })
        assert res.status_code == 404

    def test_suggest_503_on_agent_error(self, client, admin_headers, operator_a_headers):
        """Returns 503 when agent service is unavailable."""
        lead_id, _ = self._setup_lead(client, admin_headers, operator_a_headers)

        from app.services.agent import AgentServiceError
        with patch("app.routers.conversations.generate_agent_reply", side_effect=AgentServiceError("timeout")):
            res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
                "company_id": 1, "channel": "whatsapp", "lead_id": lead_id
            })
        assert res.status_code == 503

    def test_suggest_requires_auth(self, client):
        """Suggest requires authentication."""
        res = client.post("/conversations/suggest-message", json={
            "company_id": 1, "channel": "whatsapp", "lead_id": 1
        })
        assert res.status_code in (401, 403)

    def test_suggest_fallback_on_invalid_json(self, client, admin_headers, operator_a_headers):
        """Fallback to raw response when agent returns non-JSON."""
        lead_id, _ = self._setup_lead(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = "Mensagem sugerida pelo agente."
            res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
                "company_id": 1, "channel": "whatsapp", "lead_id": lead_id
            })
        assert res.status_code == 200
        data = res.json()
        assert data["suggested_message"] == "Mensagem sugerida pelo agente."

    def test_suggest_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A cannot suggest from Operator B's lead."""
        company_a = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company_a.status_code == 200
        company_b = client.post("/companies", headers=admin_headers, json={"name": "Beta", "slug": "beta"})
        assert company_b.status_code == 200
        cid_b = company_b.json()["id"]

        lead_b = client.post("/leads", headers=operator_b_headers, json={
            "company_id": cid_b, "name": "Beta Lead", "phone": "5511999999999", "source": "manual"
        })
        assert lead_b.status_code == 200

        res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
            "company_id": 1, "channel": "whatsapp", "lead_id": lead_b.json()["id"]
        })
        assert res.status_code == 404

    def test_suggest_does_not_persist(self, client, admin_headers, operator_a_headers):
        """Suggest does NOT create a conversation."""
        lead_id, _ = self._setup_lead(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"suggested_message": "Test", "reasoning": "Test"}'
            res = client.post("/conversations/suggest-message", headers=operator_a_headers, json={
                "company_id": 1, "channel": "whatsapp", "lead_id": lead_id
            })
        assert res.status_code == 200

        convs = client.get("/conversations", headers=operator_a_headers)
        if convs.status_code == 200:
            assert len(convs.json()) == 0
