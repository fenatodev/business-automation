"""WP-272: Test AI-assisted opportunity suggestion from customer context."""

import pytest
from unittest.mock import patch


class TestSuggestOpportunityFromCustomer:
    """Verify suggest-opportunity endpoint behavior for customers."""

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

    def test_suggest_returns_suggestion(self, client, admin_headers, operator_a_headers):
        """Suggest returns structured opportunity suggestion."""
        customer_id, _ = self._setup_customer(client, admin_headers, operator_a_headers)

        with patch("app.services.agent.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_title": "Projeto para customer", '
                '"suggested_description": "Novo projeto para customer existente", '
                '"suggested_budget": "R$8000", '
                '"suggested_deadline": "45 dias", '
                '"suggested_requirements": "Backend API", '
                '"reasoning": "Baseado nos dados do customer"}'
            )
            res = client.post(f"/customers/{customer_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert "suggested_title" in data
        assert "reasoning" in data
        assert data["customer_id"] == customer_id

    def test_suggest_parses_json_fields(self, client, admin_headers, operator_a_headers):
        """Suggestion fields are correctly parsed from JSON response."""
        customer_id, _ = self._setup_customer(client, admin_headers, operator_a_headers)

        with patch("app.services.agent.generate_agent_reply") as mock_gen:
            mock_gen.return_value = (
                '{"suggested_title": "Título teste", '
                '"suggested_description": "Desc teste", '
                '"suggested_budget": "R$3000", '
                '"suggested_deadline": "20 dias", '
                '"suggested_requirements": "Frontend", '
                '"reasoning": "Teste"}'
            )
            res = client.post(f"/customers/{customer_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["suggested_title"] == "Título teste"
        assert data["suggested_description"] == "Desc teste"
        assert data["suggested_budget"] == "R$3000"

    def test_suggest_fallback_on_invalid_json(self, client, admin_headers, operator_a_headers):
        """Fallback to raw response when agent returns non-JSON."""
        customer_id, _ = self._setup_customer(client, admin_headers, operator_a_headers)

        with patch("app.services.agent.generate_agent_reply") as mock_gen:
            mock_gen.return_value = "Não consegui sugerir."
            res = client.post(f"/customers/{customer_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["reasoning"] == "Não consegui sugerir."
        assert data["suggested_title"] is None

    def test_suggest_503_on_agent_error(self, client, admin_headers, operator_a_headers):
        """Returns 503 when agent service is unavailable."""
        customer_id, _ = self._setup_customer(client, admin_headers, operator_a_headers)

        from app.services.agent import AgentServiceError
        with patch("app.services.agent.generate_agent_reply", side_effect=AgentServiceError("timeout")):
            res = client.post(f"/customers/{customer_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 503

    def test_suggest_requires_auth(self, client):
        """Suggest requires authentication."""
        res = client.post("/customers/999/suggest-opportunity")
        assert res.status_code in (401, 403)

    def test_suggest_404_customer_not_found(self, client, admin_headers, operator_a_headers):
        """Returns 404 for non-existent customer."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        res = client.post("/customers/99999/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 404

    def test_suggest_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A cannot suggest from Operator B's customer."""
        company_a = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company_a.status_code == 200
        company_b = client.post("/companies", headers=admin_headers, json={"name": "Beta", "slug": "beta"})
        assert company_b.status_code == 200
        cid_b = company_b.json()["id"]

        customer_b = client.post("/customers", headers=operator_b_headers, json={
            "company_id": cid_b, "name": "Beta Customer", "phone": "5511999999999"
        })
        assert customer_b.status_code == 200

        res = client.post(f"/customers/{customer_b.json()['id']}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 404

    def test_suggest_uses_company_config(self, client, admin_headers, operator_a_headers):
        """Suggest uses company agent config (temperature, model)."""
        customer_id, cid = self._setup_customer(client, admin_headers, operator_a_headers)

        res = client.put(f"/companies/{cid}/agent-config", headers=operator_a_headers, json={
            "temperature": 0.5, "max_tokens": 250, "model": "qwen3:8b"
        })
        assert res.status_code == 200

        with patch("app.services.agent.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"suggested_title": "Test", "reasoning": "Test"}'
            res = client.post(f"/customers/{customer_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 250
        assert call_kwargs["model"] == "qwen3:8b"

    def test_suggest_does_not_persist(self, client, admin_headers, operator_a_headers):
        """Suggest does NOT create an opportunity."""
        customer_id, _ = self._setup_customer(client, admin_headers, operator_a_headers)

        with patch("app.services.agent.generate_agent_reply") as mock_gen:
            mock_gen.return_value = '{"suggested_title": "Test", "reasoning": "Test"}'
            res = client.post(f"/customers/{customer_id}/suggest-opportunity", headers=operator_a_headers)
        assert res.status_code == 200

        # Verify no opportunity was created
        opps = client.get("/opportunities", headers=operator_a_headers)
        if opps.status_code == 200:
            assert len(opps.json()) == 0
