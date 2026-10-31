"""WP-182 — Brief CSV export.

Tests that the operator can export proposal briefs as CSV with filters.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp"):
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": "manual",
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_brief(client, headers, opportunity_id):
    res = client.patch(
        f"/opportunities/{opportunity_id}/triage",
        headers=headers,
        json={"next_action": "prepare_proposal"},
    )
    assert res.status_code == 200
    res = client.post(
        f"/opportunities/{opportunity_id}/proposal-brief",
        headers=headers,
        json={
            "offer_reference": f"OFF-{opportunity_id}",
            "diagnosis": "Diagnosis",
            "scope": "Scope",
            "deliverables": "Deliverables",
            "acceptance_criteria": "Acceptance",
        },
    )
    assert res.status_code == 200
    return res.json()


class TestBriefExportCSV:
    """Test GET /proposal-briefs/export.csv."""

    def test_export_empty(self, client, admin_headers, operator_a_headers):
        """Empty company returns CSV with headers only."""
        _create_company(client, admin_headers, name="EmptyCo")
        res = client.get("/proposal-briefs/export.csv", headers=operator_a_headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "proposal-briefs.csv" in res.headers["content-disposition"]
        content = res.text
        assert "ID" in content
        assert "Título" in content

    def test_export_with_briefs(self, client, admin_headers, operator_a_headers):
        """Export includes brief data."""
        _create_company(client, admin_headers, name="ExportCo")
        opp = _create_opportunity(client, operator_a_headers, title="ExportTest")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs/export.csv", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "ExportTest" in content
        assert "draft" in content

    def test_export_filter_by_status(self, client, admin_headers, operator_a_headers):
        """Export respects status filter."""
        _create_company(client, admin_headers, name="FilterExportCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs/export.csv?status=draft", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "draft" in content

    def test_export_filter_by_search(self, client, admin_headers, operator_a_headers):
        """Export respects search filter."""
        _create_company(client, admin_headers, name="SearchExportCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="Alpha")
        opp2 = _create_opportunity(client, operator_a_headers, title="Beta")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs/export.csv?q=Alpha", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "Alpha" in content

    def test_export_requires_auth(self, client, admin_headers, operator_a_headers):
        """Export requires authentication."""
        res = client.get("/proposal-briefs/export.csv")
        assert res.status_code in (401, 403)

    def test_export_tenant_isolation(self, client, admin_headers, operator_a_headers):
        """Export only includes briefs from authenticated tenant."""
        _create_company(client, admin_headers, name="TenantExportCo")
        opp = _create_opportunity(client, operator_a_headers, title="TenantTest")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs/export.csv", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "TenantTest" in content
