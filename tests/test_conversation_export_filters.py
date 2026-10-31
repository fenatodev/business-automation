"""WP-125 — Filtered conversations CSV export."""

import pytest
from app.models import Company, Conversation, Message

from conftest import TestingSessionLocal


@pytest.fixture
def companies():
    with TestingSessionLocal() as db:
        db.add_all([
            Company(id=1, name="Synthetic A", slug="conv-a"),
            Company(id=2, name="Synthetic B", slug="conv-b"),
        ])
        db.commit()
        yield


class TestConversationExportCSVFilters:
    """GET /companies/{company_id}/conversations/export.csv with filters."""

    def _create_conversations(self, company_id):
        """Create test conversations for a company."""
        with TestingSessionLocal() as db:
            convs = [
                Conversation(id=1, company_id=company_id, channel="whatsapp", status="open"),
                Conversation(id=2, company_id=company_id, channel="email", status="closed"),
                Conversation(id=3, company_id=company_id, channel="whatsapp", status="open"),
            ]
            db.add_all(convs)
            db.add_all([
                Message(conversation_id=1, sender_type="customer", content="Hello from whatsapp"),
                Message(conversation_id=2, sender_type="customer", content="Email inquiry about pricing"),
                Message(conversation_id=3, sender_type="customer", content="Another whatsapp message"),
            ])
            db.commit()

    def test_export_csv_accepts_channel_filter(self, companies, client, operator_a_headers):
        self._create_conversations(1)
        resp = client.get(
            "/companies/1/conversations/export.csv?channel=whatsapp",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert "Hello from whatsapp" in resp.text
        assert "Another whatsapp message" in resp.text
        assert "Email inquiry" not in resp.text

    def test_export_csv_accepts_status_filter(self, companies, client, operator_a_headers):
        self._create_conversations(1)
        resp = client.get(
            "/companies/1/conversations/export.csv?status=closed",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert "Email inquiry" in resp.text
        assert "Hello from whatsapp" not in resp.text

    def test_export_csv_accepts_search_filter(self, companies, client, operator_a_headers):
        self._create_conversations(1)
        resp = client.get(
            "/companies/1/conversations/export.csv?q=pricing",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert "Email inquiry" in resp.text
        assert "Hello from whatsapp" not in resp.text

    def test_export_csv_accepts_customer_id_filter(self, companies, client, operator_a_headers):
        self._create_conversations(1)
        # No conversations have customer_id set, so filtering by customer_id=1
        # should return empty results
        resp = client.get(
            "/companies/1/conversations/export.csv?customer_id=1",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        # Should have headers but no data rows (no conversations with customer_id=1)
        assert "ID" in resp.text
        assert "Hello from whatsapp" not in resp.text

    def test_export_csv_combined_filters(self, companies, client, operator_a_headers):
        self._create_conversations(1)
        resp = client.get(
            "/companies/1/conversations/export.csv?channel=whatsapp&status=open",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert "Hello from whatsapp" in resp.text
        assert "Another whatsapp message" in resp.text
        assert "Email inquiry" not in resp.text

    def test_export_csv_empty_with_filter(self, companies, client, operator_a_headers):
        self._create_conversations(1)
        resp = client.get(
            "/companies/1/conversations/export.csv?channel=telegram",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        # Should have headers but no data rows
        assert "ID" in resp.text
        assert "Hello from whatsapp" not in resp.text

    def test_export_csv_tenant_isolation(self, companies, client, operator_a_headers, operator_b_headers):
        self._create_conversations(1)
        resp = client.get(
            "/companies/1/conversations/export.csv",
            headers=operator_b_headers,
        )
        assert resp.status_code in (403, 404)
