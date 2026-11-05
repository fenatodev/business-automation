"""WP-269: Test AI-assisted opportunity suggestion from conversation context."""

import pytest
from unittest.mock import patch


class TestSuggestOpportunity:
    """Verify suggest-opportunity endpoint behavior."""

    def _setup_conversation(self, client, admin_headers, operator_headers):
        """Create company, lead, conversation and messages — return conv_id."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        cid = company.json()["id"]

        lead = client.post("/leads", headers=operator_headers, json={
            "company_id": cid, "name": "Test Lead", "phone": "5511999999999", "source": "manual"
        })
        assert lead.status_code == 200
        lead_id = lead.json()["id"]

        conv = client.post("/conversations", headers=operator_headers, json={
            "company_id": cid, "channel": "whatsapp", "lead_id": lead_id
        })
        assert conv.status_code == 200
        conv_id = conv.json()["id"]

        msg = client.post(f"/conversations/{conv_id}/messages", headers=operator_headers, json={
            "sender_type": "customer", "content": "Preciso de um site institucional com orçamento de R$ 8.000 até dezembro."
        })
        assert msg.status_code == 200
        return conv_id, cid

    def test_suggest_opportunity_returns_suggestion(self, client, admin_headers, operator_a_headers):
        """Suggest opportunity returns structured suggestion."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_title": "Site institucional", '
                '"suggested_description": "Site institucional para empresa", '
                '"suggested_budget": "R$ 8.000", '
                '"suggested_deadline": "2025-12-31", '
                '"suggested_requirements": null, '
                '"reasoning": "Extraído da mensagem"}'
            )
            res = client.post(f"/conversations/{conv_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert "suggested_title" in data
        assert "suggested_description" in data
        assert "suggested_budget" in data
        assert "suggested_deadline" in data
        assert "suggested_requirements" in data
        assert "reasoning" in data
        assert data["conversation_id"] == conv_id

    def test_suggest_opportunity_parses_json_fields(self, client, admin_headers, operator_a_headers):
        """Suggested fields are correctly parsed from JSON response."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_title": "E-commerce", '
                '"suggested_description": "Loja virtual", '
                '"suggested_budget": "R$ 15.000", '
                '"suggested_deadline": "2026-06-30", '
                '"suggested_requirements": "Pagamento online", '
                '"reasoning": "Test"}'
            )
            res = client.post(f"/conversations/{conv_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["suggested_title"] == "E-commerce"
        assert data["suggested_budget"] == "R$ 15.000"
        assert data["suggested_requirements"] == "Pagamento online"

    def test_suggest_opportunity_fallback_on_invalid_json(self, client, admin_headers, operator_a_headers):
        """Fallback to raw response when agent returns non-JSON."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = "Não consegui extrair informações claras."
            res = client.post(f"/conversations/{conv_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["suggested_title"] is None
        assert data["suggested_description"] is None
        assert "Não consegui" in data["reasoning"]

    def test_suggest_opportunity_503_on_agent_error(self, client, admin_headers, operator_a_headers):
        """Returns 503 when agent service is unavailable."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        from app.services.agent import AgentServiceError
        with patch("app.routers.conversations.generate_agent_reply", side_effect=AgentServiceError("timeout")):
            res = client.post(f"/conversations/{conv_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 503

    def test_suggest_opportunity_requires_auth(self, client):
        """Suggest opportunity requires authentication."""
        res = client.post("/conversations/999/suggest-opportunity")
        assert res.status_code in (401, 403)

    def test_suggest_opportunity_404_conversation_not_found(self, client, admin_headers, operator_a_headers):
        """Returns 404 for non-existent conversation."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        res = client.post("/conversations/99999/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 404

    def test_suggest_opportunity_400_no_messages(self, client, admin_headers, operator_a_headers):
        """Returns 400 when conversation has no messages."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        cid = company.json()["id"]
        lead = client.post("/leads", headers=operator_a_headers, json={
            "company_id": cid, "name": "Test", "phone": "5511999999999", "source": "manual"
        })
        assert lead.status_code == 200
        conv = client.post("/conversations", headers=operator_a_headers, json={
            "company_id": cid, "channel": "whatsapp", "lead_id": lead.json()["id"]
        })
        assert conv.status_code == 200
        res = client.post(f"/conversations/{conv.json()['id']}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 400

    def test_suggest_opportunity_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A cannot suggest opportunity from Operator B's conversation."""
        company_a = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company_a.status_code == 200
        company_b = client.post("/companies", headers=admin_headers, json={"name": "Beta", "slug": "beta"})
        assert company_b.status_code == 200
        cid_b = company_b.json()["id"]

        lead_b = client.post("/leads", headers=operator_b_headers, json={
            "company_id": cid_b, "name": "Beta Lead", "phone": "5511999999999", "source": "manual"
        })
        assert lead_b.status_code == 200
        conv_b = client.post("/conversations", headers=operator_b_headers, json={
            "company_id": cid_b, "channel": "whatsapp", "lead_id": lead_b.json()["id"]
        })
        assert conv_b.status_code == 200
        conv_b_id = conv_b.json()["id"]

        msg = client.post(f"/conversations/{conv_b_id}/messages", headers=operator_b_headers, json={
            "sender_type": "customer", "content": "Test"
        })
        assert msg.status_code == 200

        res = client.post(f"/conversations/{conv_b_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 404

    def test_suggest_opportunity_uses_company_config(self, client, admin_headers, operator_a_headers):
        """Suggest opportunity uses company agent config (temperature, model)."""
        conv_id, cid = self._setup_conversation(client, admin_headers, operator_a_headers)

        res = client.put(f"/companies/{cid}/agent-config", headers=operator_a_headers, json={
            "temperature": 0.3, "max_tokens": 300, "model": "qwen3:8b"
        })
        assert res.status_code == 200

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"suggested_title": "Test", "suggested_description": null, "suggested_budget": null, "suggested_deadline": null, "suggested_requirements": null, "reasoning": "ok"}'
            res = client.post(f"/conversations/{conv_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 300
        assert call_kwargs["model"] == "qwen3:8b"
