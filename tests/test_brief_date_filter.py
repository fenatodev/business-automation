"""WP-183 — Brief date filter.

Tests that the operator can filter briefs by date range.
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


class TestBriefDateFilter:
    """Test date range filter on brief endpoints."""

    def test_list_filter_by_from_date(self, client, admin_headers, operator_a_headers):
        """from_date filters briefs created after the given date."""
        _create_company(client, admin_headers, name="DateFromCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = client.get(f"/proposal-briefs?from_date={today}", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1

    def test_list_filter_by_to_date(self, client, admin_headers, operator_a_headers):
        """to_date filters briefs created before the given date."""
        _create_company(client, admin_headers, name="DateToCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        tomorrow = (datetime.now(timezone.utc).day + 1)
        future = f"2099-12-31"
        res = client.get(f"/proposal-briefs?to_date={future}", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1

    def test_list_filter_by_date_range(self, client, admin_headers, operator_a_headers):
        """from_date and to_date together filter by range."""
        _create_company(client, admin_headers, name="DateRangeCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        future = "2099-12-31"
        res = client.get(f"/proposal-briefs?from_date={today}&to_date={future}", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1

    def test_list_filter_by_from_date_future(self, client, admin_headers, operator_a_headers):
        """from_date in the future returns empty list."""
        _create_company(client, admin_headers, name="DateFutureCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs?from_date=2099-12-31", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_count_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects date filters."""
        _create_company(client, admin_headers, name="CountDateCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = client.get(f"/proposal-briefs/count?from_date={today}", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] >= 1

    def test_export_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """Export CSV respects date filters."""
        _create_company(client, admin_headers, name="ExportDateCo")
        opp = _create_opportunity(client, operator_a_headers, title="DateExport")
        _create_brief(client, operator_a_headers, opp["id"])

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = client.get(f"/proposal-briefs/export.csv?from_date={today}", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "DateExport" in content
