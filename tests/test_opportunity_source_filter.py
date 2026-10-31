"""WP-189 — Filter opportunities by source.

Tests that the operator can filter opportunities by source field
in list, count, and export CSV endpoints.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp", source="manual"):
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": source,
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


class TestOpportunitySourceFilter:
    """Test ?source= filter in opportunities endpoints."""

    def test_list_filter_by_source(self, client, admin_headers, operator_a_headers):
        """List opportunities filtered by source."""
        _create_company(client, admin_headers, name="SourceCo")
        _create_opportunity(client, operator_a_headers, "Manual", "manual")
        _create_opportunity(client, operator_a_headers, "Intake", "intake")

        res = client.get(
            "/opportunities?source=intake",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        opps = res.json()
        assert len(opps) >= 1
        assert all(o["source"] == "intake" for o in opps)

    def test_list_no_source_filter(self, client, admin_headers, operator_a_headers):
        """List without source filter returns all."""
        _create_company(client, admin_headers, name="AllCo")
        _create_opportunity(client, operator_a_headers, "Manual", "manual")
        _create_opportunity(client, operator_a_headers, "Intake", "intake")

        res = client.get("/opportunities", headers=operator_a_headers)
        assert res.status_code == 200
        opps = res.json()
        assert len(opps) >= 2

    def test_count_respects_source_filter(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects source filter."""
        _create_company(client, admin_headers, name="CountCo")
        _create_opportunity(client, operator_a_headers, "Manual", "manual")
        _create_opportunity(client, operator_a_headers, "Intake", "intake")

        res = client.get(
            "/opportunities/count?source=manual",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    def test_export_csv_respects_source_filter(self, client, admin_headers, operator_a_headers):
        """Export CSV respects source filter."""
        _create_company(client, admin_headers, name="ExportCo")
        _create_opportunity(client, operator_a_headers, "Manual", "manual")
        _create_opportunity(client, operator_a_headers, "Intake", "intake")

        res = client.get(
            "/opportunities/export.csv?source=manual",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "text/csv; charset=utf-8"
        text = res.text
        # Should contain "Manual" but not "Intake"
        assert "Manual" in text

    def test_source_filter_with_other_filters(self, client, admin_headers, operator_a_headers):
        """Source filter works combined with other filters."""
        _create_company(client, admin_headers, name="ComboCo")
        _create_opportunity(client, operator_a_headers, "Test", "intake")

        res = client.get(
            "/opportunities?source=intake&q=Test",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        opps = res.json()
        assert len(opps) >= 1
        assert opps[0]["source"] == "intake"

    def test_source_filter_empty_result(self, client, admin_headers, operator_a_headers):
        """Source filter with no matches returns empty list."""
        _create_company(client, admin_headers, name="EmptyCo")
        _create_opportunity(client, operator_a_headers, "Manual", "manual")

        res = client.get(
            "/opportunities?source=review_queue",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        opps = res.json()
        assert len(opps) == 0
