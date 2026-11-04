"""WP-233 — Filter proposal briefs by opportunity_id.

The briefs module had status filter but not opportunity_id filter.
This WP adds ?opportunity_id= to list, count, and export CSV endpoints.
"""

import pytest


class TestBriefOpportunityFilter:
    """Test filtering proposal briefs by opportunity_id."""

    def _create_company(self, client, admin_headers, name="TestCo"):
        resp = client.post("/companies", json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
        }, headers=admin_headers)
        assert resp.status_code == 200, f"Failed to create company: {resp.text}"
        return resp.json()

    def _create_opportunity(self, client, company_id, operator_headers, title="Test", url=None):
        resp = client.post("/opportunities", json={
            "title": title,
            "description": "Test",
            "source": "manual",
            "external_url": url or f"https://example.com/{title}",
            "captured_at": "2024-01-01T00:00:00",
            "company_id": company_id,
        }, headers=operator_headers)
        assert resp.status_code == 200, f"Failed to create opportunity: {resp.text}"
        return resp.json()

    def _create_brief(self, client, operator_headers, opportunity_id):
        resp = client.post(
            f"/opportunities/{opportunity_id}/proposal-brief", json={
                "offer_reference": "REF-TEST",
                "diagnosis": "Test diagnosis",
                "scope": "Test scope",
                "deliverables": "Test deliverables",
                "acceptance_criteria": "Test criteria",
            }, headers=operator_headers)
        assert resp.status_code == 200, f"Failed to create brief: {resp.text}"
        return resp.json()

    def _triage_to_prepare(self, client, operator_headers, opportunity_id):
        """Triage opportunity to prepare_proposal so briefs can be created."""
        resp = client.patch(
            f"/opportunities/{opportunity_id}/triage", json={
                "next_action": "prepare_proposal",
            }, headers=operator_headers)
        # Ignore 400 if already triaged
        if resp.status_code not in (200, 400):
            raise AssertionError(f"Triage failed: {resp.text}")

    def test_filter_briefs_by_opportunity_id(self, client, admin_headers, operator_a_headers):
        """Filter briefs by opportunity_id returns only matching briefs."""
        company = self._create_company(client, admin_headers, "BriefFilterCo")
        # Create multiple opportunities, each with one brief
        opp1 = self._create_opportunity(client, company["id"], operator_a_headers, "Opp1", url="https://example.com/opp1")
        opp2 = self._create_opportunity(client, company["id"], operator_a_headers, "Opp2", url="https://example.com/opp2")
        opp3 = self._create_opportunity(client, company["id"], operator_a_headers, "Opp3", url="https://example.com/opp3")

        self._triage_to_prepare(client, operator_a_headers, opp1["id"])
        self._create_brief(client, operator_a_headers, opp1["id"])
        self._triage_to_prepare(client, operator_a_headers, opp2["id"])
        self._create_brief(client, operator_a_headers, opp2["id"])
        self._triage_to_prepare(client, operator_a_headers, opp3["id"])
        self._create_brief(client, operator_a_headers, opp3["id"])

        response = client.get(
            "/proposal-briefs?opportunity_id=" + str(opp1["id"]),
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        briefs = response.json()
        assert len(briefs) == 1
        assert briefs[0]["opportunity_id"] == opp1["id"]

    def test_filter_briefs_by_opportunity_id_returns_empty(self, client, admin_headers, operator_a_headers):
        """Filter by non-existent opportunity_id returns empty list."""
        company = self._create_company(client, admin_headers, "BriefEmptyCo")
        opp = self._create_opportunity(client, company["id"], operator_a_headers)
        self._triage_to_prepare(client, operator_a_headers, opp["id"])
        self._create_brief(client, operator_a_headers, opp["id"])

        response = client.get(
            "/proposal-briefs?opportunity_id=99999",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_count_briefs_by_opportunity_id(self, client, admin_headers, operator_a_headers):
        """Count briefs respects opportunity_id filter."""
        company = self._create_company(client, admin_headers, "BriefCountCo")
        opp1 = self._create_opportunity(client, company["id"], operator_a_headers, "Count1", url="https://example.com/count1")
        opp2 = self._create_opportunity(client, company["id"], operator_a_headers, "Count2", url="https://example.com/count2")

        self._triage_to_prepare(client, operator_a_headers, opp1["id"])
        self._create_brief(client, operator_a_headers, opp1["id"])
        self._triage_to_prepare(client, operator_a_headers, opp2["id"])
        self._create_brief(client, operator_a_headers, opp2["id"])

        response = client.get(
            "/proposal-briefs/count?opportunity_id=" + str(opp1["id"]),
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_export_csv_respects_opportunity_id(self, client, admin_headers, operator_a_headers):
        """Export CSV respects opportunity_id filter."""
        company = self._create_company(client, admin_headers, "BriefExportCo")
        opp1 = self._create_opportunity(client, company["id"], operator_a_headers, "Exp1", url="https://example.com/exp1")
        opp2 = self._create_opportunity(client, company["id"], operator_a_headers, "Exp2", url="https://example.com/exp2")

        self._triage_to_prepare(client, operator_a_headers, opp1["id"])
        self._create_brief(client, operator_a_headers, opp1["id"])
        self._triage_to_prepare(client, operator_a_headers, opp2["id"])
        self._create_brief(client, operator_a_headers, opp2["id"])

        response = client.get(
            "/proposal-briefs/export.csv?opportunity_id=" + str(opp1["id"]),
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        content = response.text
        lines = [l for l in content.strip().split("\n") if l]
        # Header + 1 data row for opp1
        assert len(lines) == 2

    def test_opportunity_id_filter_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Opportunity filter cannot access briefs from another tenant."""
        company_a = self._create_company(client, admin_headers, "TenantBriefA")
        self._create_company(client, admin_headers, "TenantBriefB")
        opp = self._create_opportunity(client, company_a["id"], operator_a_headers, "TenantOpp", url="https://example.com/tenant")
        self._triage_to_prepare(client, operator_a_headers, opp["id"])
        self._create_brief(client, operator_a_headers, opp["id"])

        # Operator B queries with opportunity from company A — the JOIN ensures tenant isolation
        # Returns empty list (200 OK) because the opportunity doesn't belong to operator B's tenant
        response = client.get(
            "/proposal-briefs?opportunity_id=" + str(opp["id"]),
            headers=operator_b_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_opportunity_id_filter_combined_with_status(self, client, admin_headers, operator_a_headers):
        """opportunity_id and status filters work together."""
        company = self._create_company(client, admin_headers, "CombinedBriefCo")
        opp = self._create_opportunity(client, company["id"], operator_a_headers, "Combined", url="https://example.com/combined")

        self._triage_to_prepare(client, operator_a_headers, opp["id"])
        self._create_brief(client, operator_a_headers, opp["id"])

        response = client.get(
            "/proposal-briefs?opportunity_id=" + str(opp["id"]) + "&status=draft",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_opportunity_id_filter_with_pagination(self, client, admin_headers, operator_a_headers):
        """Opportunity filter works with pagination."""
        company = self._create_company(client, admin_headers, "BriefPageCo")
        # Create multiple opportunities with briefs
        opps = []
        for i in range(5):
            opp = self._create_opportunity(client, company["id"], operator_a_headers, f"Page{i}", url=f"https://example.com/page{i}")
            self._triage_to_prepare(client, operator_a_headers, opp["id"])
            self._create_brief(client, operator_a_headers, opp["id"])
            opps.append(opp)

        # Filter by first opportunity — should return 1
        response = client.get(
            "/proposal-briefs?opportunity_id=" + str(opps[0]["id"]) + "&limit=2&offset=0",
            headers=operator_a_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
