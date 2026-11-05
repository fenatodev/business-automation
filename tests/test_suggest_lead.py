"""WP-267: Test AI-assisted lead suggestion from conversation context."""

import pytest
from unittest.mock import patch


class TestSuggestLead:
    """Verify suggest-lead endpoint behavior."""

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
            "sender_type": "customer", "content": "Olá, preciso de um site para minha loja."
        })
        assert msg.status_code == 200
        return conv_id, cid

    def test_suggest_lead_returns_suggestion(self, client, admin_headers, operator_a_headers):
        """Suggest lead returns structured suggestion."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_name": "João Silva", '
                '"suggested_phone": "11999999999", '
                '"suggested_interest": "Site para loja", '
                '"reasoning": "Extraído da mensagem"}'
            )
            res = client.post(f"/conversations/{conv_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert "suggested_name" in data
        assert "suggested_phone" in data
        assert "suggested_interest" in data
        assert "reasoning" in data
        assert data["conversation_id"] == conv_id

    def test_suggest_lead_parses_json_fields(self, client, admin_headers, operator_a_headers):
        """Suggested fields are correctly parsed from JSON response."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_name": "Maria", '
                '"suggested_phone": "21987654321", '
                '"suggested_interest": "Orçamento", '
                '"reasoning": "Test"}'
            )
            res = client.post(f"/conversations/{conv_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["suggested_name"] == "Maria"
        assert data["suggested_phone"] == "21987654321"
        assert data["suggested_interest"] == "Orçamento"

    def test_suggest_lead_fallback_on_invalid_json(self, client, admin_headers, operator_a_headers):
        """Fallback to raw response when agent returns non-JSON."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = "Não consegui extrair informações claras."
            res = client.post(f"/conversations/{conv_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["suggested_name"] is None
        assert data["suggested_phone"] is None
        assert data["suggested_interest"] is None
        assert "Não consegui" in data["reasoning"]

    def test_suggest_lead_503_on_agent_error(self, client, admin_headers, operator_a_headers):
        """Returns 503 when agent service is unavailable."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        from app.services.agent import AgentServiceError
        with patch("app.routers.conversations.generate_agent_reply", side_effect=AgentServiceError("timeout")):
            res = client.post(f"/conversations/{conv_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 503

    def test_suggest_lead_requires_auth(self, client):
        """Suggest lead requires authentication."""
        res = client.post("/conversations/999/suggest-lead")
        assert res.status_code in (401, 403)

    def test_suggest_lead_404_conversation_not_found(self, client, admin_headers, operator_a_headers):
        """Returns 404 for non-existent conversation."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        res = client.post("/conversations/99999/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 404

    def test_suggest_lead_400_no_messages(self, client, admin_headers, operator_a_headers):
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
        res = client.post(f"/conversations/{conv.json()['id']}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 400

    def test_suggest_lead_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A cannot suggest lead from Operator B's conversation."""
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

        res = client.post(f"/conversations/{conv_b_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 404

    def test_suggest_lead_does_not_persist(self, client, admin_headers, operator_a_headers):
        """Suggest lead does NOT create a lead — it only returns suggestion."""
        conv_id, cid = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_name": "Pedro", '
                '"suggested_phone": "11912345678", '
                '"suggested_interest": null, '
                '"reasoning": "Test"}'
            )
            res = client.post(f"/conversations/{conv_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 200

        leads_res = client.get("/leads", headers=operator_a_headers)
        assert leads_res.status_code == 200
        # Only the original test lead exists, no new one created
        assert all(l["name"] == "Test Lead" for l in leads_res.json())

    def test_suggest_lead_uses_company_config(self, client, admin_headers, operator_a_headers):
        """Suggest lead uses company agent config (temperature, model)."""
        conv_id, cid = self._setup_conversation(client, admin_headers, operator_a_headers)

        # Set agent config using operator (tenant-isolated)
        res = client.put(f"/companies/{cid}/agent-config", headers=operator_a_headers, json={
            "temperature": 0.5, "max_tokens": 200, "model": "qwen3:8b"
        })
        assert res.status_code == 200

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"suggested_name": "Test", "suggested_phone": null, "suggested_interest": null, "reasoning": "ok"}'
            res = client.post(f"/conversations/{conv_id}/suggest-lead", headers=operator_a_headers)
        assert res.status_code == 200
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 200
        assert call_kwargs["model"] == "qwen3:8b"
