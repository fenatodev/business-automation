"""WP-232 — Filter conversations by lead_id.

The conversations module had customer_id filter but not lead_id.
This WP adds lead_id filtering to list, count, and export CSV endpoints.
"""

import pytest


class TestConversationLeadFilter:
    """Test filtering conversations by lead_id."""

    def _create_company(self, client, admin_headers, name="TestCo"):
        resp = client.post("/companies", json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
        }, headers=admin_headers)
        assert resp.status_code == 200, f"Failed to create company: {resp.text}"
        return resp.json()

    def _create_lead(self, client, operator_headers, company_id, name="TestLead"):
        resp = client.post("/leads", json={
            "name": name,
            "phone": "555-0000",
            "source": "test",
            "company_id": company_id,
        }, headers=operator_headers)
        assert resp.status_code == 200, f"Failed to create lead: {resp.text}"
        return resp.json()

    def _create_conversation(self, client, operator_headers, company_id, lead_id=None, customer_id=None):
        data = {
            "company_id": company_id,
            "channel": "web",
        }
        if lead_id:
            data["lead_id"] = lead_id
        if customer_id:
            data["customer_id"] = customer_id
        resp = client.post("/conversations", json=data, headers=operator_headers)
        assert resp.status_code == 200, f"Failed to create conversation: {resp.text}"
        return resp.json()

    def test_filter_conversations_by_lead_id(self, client, admin_headers, operator_a_headers):
        """Filter conversations by lead_id returns only matching conversations."""
        company = self._create_company(client, admin_headers, "LeadFilterCo")
        lead1 = self._create_lead(client, operator_a_headers, company["id"], "Lead1")
        lead2 = self._create_lead(client, operator_a_headers, company["id"], "Lead2")

        conv1 = self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead1["id"])
        conv2 = self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead2["id"])

        response = client.get(
            f"/companies/{company['id']}/conversations?lead_id={lead1['id']}",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        convs = response.json()
        assert len(convs) == 1
        assert convs[0]["id"] == conv1["id"]

    def test_filter_conversations_by_lead_id_returns_empty(self, client, admin_headers, operator_a_headers):
        """Filter by non-existent lead_id returns empty list."""
        company = self._create_company(client, admin_headers, "LeadEmptyCo")
        lead = self._create_lead(client, operator_a_headers, company["id"])
        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

        response = client.get(
            f"/companies/{company['id']}/conversations?lead_id=99999",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_count_conversations_by_lead_id(self, client, admin_headers, operator_a_headers):
        """Count conversations respects lead_id filter."""
        company = self._create_company(client, admin_headers, "LeadCountCo")
        lead1 = self._create_lead(client, operator_a_headers, company["id"], "Lead1")
        lead2 = self._create_lead(client, operator_a_headers, company["id"], "Lead2")

        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead1["id"])
        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead1["id"])
        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead2["id"])

        response = client.get(
            f"/companies/{company['id']}/conversations/count?lead_id={lead1['id']}",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_export_csv_respects_lead_id(self, client, admin_headers, operator_a_headers):
        """Export CSV respects lead_id filter."""
        company = self._create_company(client, admin_headers, "LeadExportCo")
        lead1 = self._create_lead(client, operator_a_headers, company["id"], "Lead1")
        lead2 = self._create_lead(client, operator_a_headers, company["id"], "Lead2")

        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead1["id"])
        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead1["id"])
        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead2["id"])

        response = client.get(
            f"/companies/{company['id']}/conversations/export.csv?lead_id={lead1['id']}",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        content = response.text
        # Count data rows (excluding header)
        lines = [l for l in content.strip().split("\n") if l]
        # Header + 2 data rows for lead1
        assert len(lines) == 3

    def test_lead_id_filter_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Lead filter cannot access conversations from another tenant."""
        company_a = self._create_company(client, admin_headers, "TenantLeadA")
        self._create_company(client, admin_headers, "TenantLeadB")
        lead = self._create_lead(client, operator_a_headers, company_a["id"])
        self._create_conversation(client, operator_a_headers, company_a["id"], lead_id=lead["id"])

        # Operator B queries with lead from company A
        response = client.get(
            f"/companies/{company_a['id']}/conversations?lead_id={lead['id']}",
            headers=operator_b_headers,
        )
        assert response.status_code == 403

    def test_lead_id_filter_combined_with_customer_id(self, client, admin_headers, operator_a_headers):
        """lead_id and customer_id filters work independently."""
        company = self._create_company(client, admin_headers, "CombinedCo")
        lead = self._create_lead(client, operator_a_headers, company["id"])
        conv = self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

        # Filter by lead_id returns the conversation
        response = client.get(
            f"/companies/{company['id']}/conversations?lead_id={lead['id']}",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Filter by non-existent customer_id returns empty
        response = client.get(
            f"/companies/{company['id']}/conversations?customer_id=99999",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_lead_id_filter_with_pagination(self, client, admin_headers, operator_a_headers):
        """Lead filter works with pagination."""
        company = self._create_company(client, admin_headers, "LeadPageCo")
        lead = self._create_lead(client, operator_a_headers, company["id"])

        for i in range(5):
            self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

        response = client.get(
            f"/companies/{company['id']}/conversations?lead_id={lead['id']}&limit=2&offset=0",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_lead_id_filter_with_search(self, client, admin_headers, operator_a_headers):
        """Lead filter works with keyword search."""
        company = self._create_company(client, admin_headers, "LeadSearchCo")
        lead = self._create_lead(client, operator_a_headers, company["id"])
        self._create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

        response = client.get(
            f"/companies/{company['id']}/conversations?lead_id={lead['id']}&q=test",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        # Search may return 0 if no messages match, but should not error
        assert isinstance(response.json(), list)
