"""WP-141 — Bulk operations em conversas.

Testa o endpoint POST /conversations/bulk-status para fechar/reabrir
múltiplas conversas de uma vez, com tenant isolation e autenticação.
"""


class TestBulkConversationStatus:
    """Test bulk status update for conversations."""

    def _create_company(self, client, headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_conversation(self, client, company_id, headers):
        lead_resp = client.post("/leads", json={
            "company_id": company_id,
            "name": "Test Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=headers)
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        resp = client.post("/conversations", json={
            "company_id": company_id,
            "channel": "whatsapp",
            "lead_id": lead_id,
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_bulk_close_conversations(self, client, admin_headers, operator_a_headers):
        """Bulk close multiple conversations."""
        company = self._create_company(client, admin_headers)
        conv1 = self._create_conversation(client, company["id"], operator_a_headers)
        conv2 = self._create_conversation(client, company["id"], operator_a_headers)

        resp = client.post(
            "/conversations/bulk-status",
            json={
                "conversation_ids": [conv1["id"], conv2["id"]],
                "status": "closed",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 2
        assert set(data["updated_ids"]) == {conv1["id"], conv2["id"]}
        assert data["skipped"] == []

    def test_bulk_reopen_conversations(self, client, admin_headers, operator_a_headers):
        """Bulk reopen closed conversations."""
        company = self._create_company(client, admin_headers)
        conv1 = self._create_conversation(client, company["id"], operator_a_headers)
        conv2 = self._create_conversation(client, company["id"], operator_a_headers)

        # Close them first
        client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": [conv1["id"], conv2["id"]], "status": "closed"},
            headers=operator_a_headers,
        )

        # Reopen
        resp = client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": [conv1["id"], conv2["id"]], "status": "open"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2

    def test_bulk_skips_nonexistent(self, client, admin_headers, operator_a_headers):
        """Bulk update skips IDs that don't exist."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)

        resp = client.post(
            "/conversations/bulk-status",
            json={
                "conversation_ids": [conv["id"], 99999, 88888],
                "status": "closed",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 1
        assert data["updated_ids"] == [conv["id"]]
        assert set(data["skipped"]) == {99999, 88888}

    def test_bulk_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot bulk update conversations from another company."""
        company_a = self._create_company(client, admin_headers)
        conv_a = self._create_conversation(client, company_a["id"], operator_a_headers)

        company_b = client.post("/companies", json={
            "name": "Company B", "slug": "company-b",
        }, headers=admin_headers).json()
        conv_b = self._create_conversation(client, company_b["id"], operator_b_headers)

        # Try to close conv_b with operator_a's token
        resp = client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": [conv_b["id"]], "status": "closed"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 0
        assert data["skipped"] == [conv_b["id"]]

    def test_bulk_requires_auth(self, client, admin_headers, operator_a_headers):
        """Bulk status requires authentication."""
        resp = client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": [1], "status": "closed"},
        )
        assert resp.status_code in (401, 403)

    def test_bulk_empty_list_rejected(self, client, admin_headers, operator_a_headers):
        """Empty conversation_ids list should be rejected."""
        resp = client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": [], "status": "closed"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 422

    def test_bulk_max_100_ids(self, client, admin_headers, operator_a_headers):
        """More than 100 IDs should be rejected."""
        resp = client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": list(range(1, 102)), "status": "closed"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 422

    def test_bulk_invalid_status_rejected(self, client, admin_headers, operator_a_headers):
        """Invalid status should be rejected."""
        resp = client.post(
            "/conversations/bulk-status",
            json={"conversation_ids": [1], "status": "invalid"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 422
