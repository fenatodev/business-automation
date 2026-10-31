"""WP-132 — Message pagination for conversations."""

import pytest


class TestMessagePagination:
    """GET /conversations/{id}/messages with limit/offset pagination."""

    def _create_conversation_with_messages(self, client, admin_headers, operator_a_headers, num_messages=10):
        """Create a conversation with multiple messages."""
        # operator_a is tied to company_id=1 in conftest
        client.post("/companies", json={"name": "Test Co", "slug": "test-msg"}, headers=admin_headers)
        # Create a lead first (conversation requires lead_id or customer_id)
        client.post(
            "/leads",
            json={"company_id": 1, "name": "Test Lead", "phone": "11999999999", "source": "test"},
            headers=operator_a_headers,
        )
        resp = client.post(
            "/conversations",
            json={"company_id": 1, "channel": "whatsapp", "lead_id": 1, "customer_id": None},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        conv_id = resp.json()["id"]

        for i in range(num_messages):
            client.post(
                f"/conversations/{conv_id}/messages",
                json={"sender_type": "customer", "content": f"Message {i}"},
                headers=operator_a_headers,
            )
        return conv_id

    def test_list_messages_default_pagination(self, client, admin_headers, operator_a_headers):
        """Default pagination should return up to 50 messages."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        resp = client.get(f"/conversations/{conv_id}/messages", headers=operator_a_headers)
        assert resp.status_code == 200
        messages = resp.json()
        assert len(messages) == 10

    def test_list_messages_with_limit(self, client, admin_headers, operator_a_headers):
        """Limit parameter should restrict the number of messages returned."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        resp = client.get(f"/conversations/{conv_id}/messages?limit=3", headers=operator_a_headers)
        assert resp.status_code == 200
        messages = resp.json()
        assert len(messages) == 3

    def test_list_messages_with_offset(self, client, admin_headers, operator_a_headers):
        """Offset parameter should skip messages."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        resp = client.get(f"/conversations/{conv_id}/messages?limit=3&offset=5", headers=operator_a_headers)
        assert resp.status_code == 200
        messages = resp.json()
        assert len(messages) == 3

    def test_list_messages_pagination_order(self, client, admin_headers, operator_a_headers):
        """Messages should be returned in ascending ID order."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        resp = client.get(f"/conversations/{conv_id}/messages?limit=5&offset=0", headers=operator_a_headers)
        assert resp.status_code == 200
        messages = resp.json()
        ids = [msg["id"] for msg in messages]
        assert ids == sorted(ids)

    def test_list_messages_full_pagination(self, client, admin_headers, operator_a_headers):
        """Full pagination should retrieve all messages."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        page1 = client.get(f"/conversations/{conv_id}/messages?limit=3&offset=0", headers=operator_a_headers).json()
        page2 = client.get(f"/conversations/{conv_id}/messages?limit=3&offset=3", headers=operator_a_headers).json()
        page3 = client.get(f"/conversations/{conv_id}/messages?limit=3&offset=6", headers=operator_a_headers).json()
        assert len(page1) == 3
        assert len(page2) == 3
        assert len(page3) == 3
        # No more messages after offset 9
        page4 = client.get(f"/conversations/{conv_id}/messages?limit=3&offset=9", headers=operator_a_headers).json()
        assert len(page4) == 1

    def test_count_messages(self, client, admin_headers, operator_a_headers):
        """GET /count should return total message count."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        resp = client.get(f"/conversations/{conv_id}/messages/count", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert data["total"] == 10

    def test_count_messages_empty_conversation(self, client, admin_headers, operator_a_headers):
        """Count should return 0 for empty conversation."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-empty"}, headers=admin_headers)
        client.post(
            "/leads",
            json={"company_id": 1, "name": "Test Lead", "phone": "11999999999", "source": "test"},
            headers=operator_a_headers,
        )
        resp = client.post(
            "/conversations",
            json={"company_id": 1, "channel": "web", "lead_id": 1, "customer_id": None},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        conv_id = resp.json()["id"]
        resp = client.get(f"/conversations/{conv_id}/messages/count", headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_messages_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator B should not access Operator A's conversation messages."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 5)
        resp = client.get(f"/conversations/{conv_id}/messages", headers=operator_b_headers)
        assert resp.status_code == 404

    def test_list_messages_limit_max(self, client, admin_headers, operator_a_headers):
        """Limit should be capped at 100."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 10)
        resp = client.get(f"/conversations/{conv_id}/messages?limit=100", headers=operator_a_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 10

    def test_list_messages_invalid_limit(self, client, admin_headers, operator_a_headers):
        """Invalid limit should return 422."""
        conv_id = self._create_conversation_with_messages(client, admin_headers, operator_a_headers, 5)
        resp = client.get(f"/conversations/{conv_id}/messages?limit=0", headers=operator_a_headers)
        assert resp.status_code == 422
        resp = client.get(f"/conversations/{conv_id}/messages?limit=101", headers=operator_a_headers)
        assert resp.status_code == 422
