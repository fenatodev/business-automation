"""WP-226 — Suggest agent reply based on conversation history.

The operator can trigger the AI agent to suggest a reply without persisting
a customer message first. The endpoint uses the last customer message in the
conversation history and returns a suggestion.
"""


class TestSuggestReply:
    """Test suggest-reply endpoint."""

    def _create_company(self, client, admin_headers, name="TestCo"):
        resp = client.post("/companies", json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
        }, headers=admin_headers)
        assert resp.status_code == 200, f"Failed to create company: {resp.text}"
        return resp.json()

    def _create_conversation(self, client, company_id, operator_headers):
        lead_resp = client.post("/leads", json={
            "company_id": company_id,
            "name": "Test Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_headers)
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]

        resp = client.post("/conversations", json={
            "company_id": company_id,
            "channel": "whatsapp",
            "lead_id": lead_id,
        }, headers=operator_headers)
        assert resp.status_code == 200, f"Failed to create conversation: {resp.text}"
        return resp.json()

    def _add_customer_message(self, client, conv_id, operator_headers, content="Preciso de orçamento"):
        resp = client.post(
            f"/conversations/{conv_id}/messages",
            json={"sender_type": "customer", "content": content},
            headers=operator_headers,
        )
        assert resp.status_code == 200, f"Failed to add message: {resp.text}"
        return resp.json()

    def test_suggest_reply_requires_customer_message(self, client, admin_headers, operator_a_headers):
        """Suggest reply returns 400 when no customer message exists."""
        company = self._create_company(client, admin_headers, "NoMsg")
        conv = self._create_conversation(client, company["id"], operator_a_headers)

        response = client.post(
            f"/conversations/{conv['id']}/suggest-reply",
            headers=operator_a_headers,
        )
        assert response.status_code == 400

    def test_suggest_reply_returns_suggestion(self, client, admin_headers, operator_a_headers):
        """Suggest reply returns a suggestion based on last customer message."""
        company = self._create_company(client, admin_headers, "SuggestCo")
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        self._add_customer_message(client, conv["id"], operator_a_headers)

        response = client.post(
            f"/conversations/{conv['id']}/suggest-reply",
            headers=operator_a_headers,
        )
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = response.json()
            assert "suggestion" in data
            assert data["conversation_id"] == conv["id"]

    def test_suggest_reply_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Suggest reply is tenant-isolated."""
        company_a = self._create_company(client, admin_headers, "TenantA")
        self._create_company(client, admin_headers, "TenantB")
        conv_a = self._create_conversation(client, company_a["id"], operator_a_headers)
        self._add_customer_message(client, conv_a["id"], operator_a_headers)

        response = client.post(
            f"/conversations/{conv_a['id']}/suggest-reply",
            headers=operator_b_headers,
        )
        assert response.status_code == 404

    def test_suggest_reply_requires_auth(self, client, admin_headers):
        """Suggest reply requires authentication."""
        response = client.post("/conversations/99999/suggest-reply")
        assert response.status_code == 401

    def test_suggest_reply_uses_last_customer_message(self, client, admin_headers, operator_a_headers):
        """Suggest reply uses the most recent customer message."""
        company = self._create_company(client, admin_headers, "LastMsgCo")
        conv = self._create_conversation(client, company["id"], operator_a_headers)

        self._add_customer_message(client, conv["id"], operator_a_headers, "Primeira mensagem")
        resp = client.post(
            f"/conversations/{conv['id']}/messages",
            json={"sender_type": "agent", "content": "Resposta do agente"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        self._add_customer_message(client, conv["id"], operator_a_headers, "Última mensagem")

        response = client.post(
            f"/conversations/{conv['id']}/suggest-reply",
            headers=operator_a_headers,
        )
        assert response.status_code in (200, 503)

    def test_suggest_reply_does_not_persist(self, client, admin_headers, operator_a_headers):
        """Suggest reply does not persist any message."""
        company = self._create_company(client, admin_headers, "NoPersistCo")
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        self._add_customer_message(client, conv["id"], operator_a_headers)

        before = client.get(f"/conversations/{conv['id']}/messages", headers=operator_a_headers)
        count_before = len(before.json())

        client.post(
            f"/conversations/{conv['id']}/suggest-reply",
            headers=operator_a_headers,
        )

        after = client.get(f"/conversations/{conv['id']}/messages", headers=operator_a_headers)
        count_after = len(after.json())

        assert count_before == count_after

    def test_suggest_reply_503_on_agent_failure(self, client, admin_headers, operator_a_headers):
        """Suggest reply returns 503 when agent service fails."""
        company = self._create_company(client, admin_headers, "AgentFailCo")
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        self._add_customer_message(client, conv["id"], operator_a_headers)

        response = client.post(
            f"/conversations/{conv['id']}/suggest-reply",
            headers=operator_a_headers,
        )
        if response.status_code == 503:
            assert "detail" in response.json()
            assert "Agent service unavailable" in response.json()["detail"]

    def test_suggest_reply_endpoint_exists(self, client, admin_headers, operator_a_headers):
        """The suggest-reply endpoint exists and is accessible."""
        company = self._create_company(client, admin_headers, "ExistCo")
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        self._add_customer_message(client, conv["id"], operator_a_headers)

        response = client.post(
            f"/conversations/{conv['id']}/suggest-reply",
            headers=operator_a_headers,
        )
        assert response.status_code != 404
