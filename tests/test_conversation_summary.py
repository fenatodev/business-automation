"""WP-270: Test AI-assisted conversation summary."""

import pytest
from unittest.mock import patch


class TestConversationSummary:
    """Verify summarize endpoint behavior."""

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

        # Add multiple messages for summary
        for msg_data in [
            {"sender_type": "customer", "content": "Olá, preciso de um site para minha empresa."},
            {"sender_type": "agent", "content": "Claro! Posso ajudar com isso. Qual é o orçamento?"},
            {"sender_type": "customer", "content": "O orçamento é de R$5000 e preciso em 30 dias."},
        ]:
            msg = client.post(f"/conversations/{conv_id}/messages", headers=operator_headers, json=msg_data)
            assert msg.status_code == 200
        return conv_id, cid

    def test_summarize_returns_summary(self, client, admin_headers, operator_a_headers):
        """Summarize returns structured summary."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"summary": "Cliente precisa de site empresarial.", '
                '"key_points": ["Orçamento R$5000", "Prazo 30 dias"], '
                '"action_items": ["Criar proposta de site"]}'
            )
            res = client.post(f"/conversations/{conv_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "key_points" in data
        assert "action_items" in data
        assert data["conversation_id"] == conv_id

    def test_summarize_parses_json_fields(self, client, admin_headers, operator_a_headers):
        """Summary fields are correctly parsed from JSON response."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"summary": "Resumo de teste", '
                '"key_points": ["Ponto 1", "Ponto 2"], '
                '"action_items": ["Ação 1"]}'
            )
            res = client.post(f"/conversations/{conv_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["summary"] == "Resumo de teste"
        assert data["key_points"] == ["Ponto 1", "Ponto 2"]
        assert data["action_items"] == ["Ação 1"]

    def test_summarize_fallback_on_invalid_json(self, client, admin_headers, operator_a_headers):
        """Fallback to raw response when agent returns non-JSON."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = "Não consegui resumir a conversa."
            res = client.post(f"/conversations/{conv_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["summary"] == "Não consegui resumir a conversa."
        assert data["key_points"] == []
        assert data["action_items"] == []

    def test_summarize_503_on_agent_error(self, client, admin_headers, operator_a_headers):
        """Returns 503 when agent service is unavailable."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        from app.services.agent import AgentServiceError
        with patch("app.routers.conversations.generate_agent_reply", side_effect=AgentServiceError("timeout")):
            res = client.post(f"/conversations/{conv_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 503

    def test_summarize_requires_auth(self, client):
        """Summarize requires authentication."""
        res = client.post("/conversations/999/summarize")
        assert res.status_code in (401, 403)

    def test_summarize_404_conversation_not_found(self, client, admin_headers, operator_a_headers):
        """Returns 404 for non-existent conversation."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        res = client.post("/conversations/99999/summarize", headers=operator_a_headers)
        assert res.status_code == 404

    def test_summarize_400_not_enough_messages(self, client, admin_headers, operator_a_headers):
        """Returns 400 when conversation has fewer than 2 messages."""
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
        # Only one message
        msg = client.post(f"/conversations/{conv.json()['id']}/messages", headers=operator_a_headers, json={
            "sender_type": "customer", "content": "Olá"
        })
        assert msg.status_code == 200
        res = client.post(f"/conversations/{conv.json()['id']}/summarize", headers=operator_a_headers)
        assert res.status_code == 400

    def test_summarize_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A cannot summarize Operator B's conversation."""
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

        for msg_data in [
            {"sender_type": "customer", "content": "Olá"},
            {"sender_type": "agent", "content": "Oi"},
        ]:
            msg = client.post(f"/conversations/{conv_b_id}/messages", headers=operator_b_headers, json=msg_data)
            assert msg.status_code == 200

        res = client.post(f"/conversations/{conv_b_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 404

    def test_summarize_uses_company_config(self, client, admin_headers, operator_a_headers):
        """Summarize uses company agent config (temperature, model)."""
        conv_id, cid = self._setup_conversation(client, admin_headers, operator_a_headers)

        res = client.put(f"/companies/{cid}/agent-config", headers=operator_a_headers, json={
            "temperature": 0.3, "max_tokens": 300, "model": "qwen3:8b"
        })
        assert res.status_code == 200

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"summary": "Test", "key_points": [], "action_items": []}'
            res = client.post(f"/conversations/{conv_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 200
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 300
        assert call_kwargs["model"] == "qwen3:8b"

    def test_summarize_empty_key_points_and_actions(self, client, admin_headers, operator_a_headers):
        """Empty key_points and action_items are valid."""
        conv_id, _ = self._setup_conversation(client, admin_headers, operator_a_headers)

        with patch("app.routers.conversations.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"summary": "Conversa simples", "key_points": [], "action_items": []}'
            res = client.post(f"/conversations/{conv_id}/summarize", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["key_points"] == []
        assert data["action_items"] == []
