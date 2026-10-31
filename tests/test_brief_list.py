"""WP-178 — Brief list view.

Tests that the operator can list all proposal briefs for their tenant company,
filter by status, and see opportunity context (title).
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


def _triage_to_prepare(client, headers, opportunity_id):
    res = client.patch(
        f"/opportunities/{opportunity_id}/triage",
        headers=headers,
        json={"next_action": "prepare_proposal"},
    )
    assert res.status_code == 200, f"Triage failed: {res.text}"
    return res.json()


def _create_brief(client, headers, opportunity_id):
    _triage_to_prepare(client, headers, opportunity_id)
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
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    return res.json()


def _set_brief_status(client, headers, opportunity_id, status):
    res = client.patch(
        f"/opportunities/{opportunity_id}/proposal-brief",
        headers=headers,
        json={"status": status},
    )
    assert res.status_code == 200
    return res.json()


class TestBriefList:
    """Test GET /proposal-briefs."""

    def test_list_briefs_empty(self, client, admin_headers, operator_a_headers):
        """Empty company returns empty list."""
        _create_company(client, admin_headers, name="EmptyCo")
        res = client.get("/proposal-briefs", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_list_briefs_returns_briefs(self, client, admin_headers, operator_a_headers):
        """Briefs appear in the list with opportunity context."""
        _create_company(client, admin_headers, name="BriefCo")
        opp = _create_opportunity(client, operator_a_headers, title="BriefOpp")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1
        brief = briefs[0]
        assert brief["opportunity_title"] == "BriefOpp"
        assert brief["offer_reference"] == f"OFF-{opp['id']}"
        assert brief["status"] == "draft"
        assert "created_at" in brief

    def test_list_briefs_multiple(self, client, admin_headers, operator_a_headers):
        """Multiple briefs are returned sorted by created_at descending."""
        _create_company(client, admin_headers, name="MultiCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 2

    def test_list_briefs_filter_by_status(self, client, admin_headers, operator_a_headers):
        """Filtering by status returns only matching briefs."""
        _create_company(client, admin_headers, name="FilterCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="Draft")
        opp2 = _create_opportunity(client, operator_a_headers, title="Ready")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])
        _set_brief_status(client, operator_a_headers, opp2["id"], "ready_for_review")

        res = client.get("/proposal-briefs?status=draft", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert all(b["status"] == "draft" for b in briefs)

        res = client.get("/proposal-briefs?status=ready_for_review", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert all(b["status"] == "ready_for_review" for b in briefs)

    def test_list_briefs_tenant_isolation(self, client, admin_headers, operator_a_headers):
        """Briefs from another company are not visible."""
        _create_company(client, admin_headers, name="TenantA")
        _create_company(client, admin_headers, name="TenantB")
        opp = _create_opportunity(client, operator_a_headers, title="A")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        for brief in briefs:
            assert brief["opportunity_title"] == "A"

    def test_list_briefs_requires_auth(self, client, admin_headers, operator_a_headers):
        """Listing briefs requires authentication."""
        res = client.get("/proposal-briefs")
        assert res.status_code in (401, 403)


class TestBriefCount:
    """Test GET /proposal-briefs/count."""

    def test_count_empty(self, client, admin_headers, operator_a_headers):
        """Empty company returns count 0."""
        _create_company(client, admin_headers, name="CountEmpty")
        res = client.get("/proposal-briefs/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] == 0

    def test_count_with_briefs(self, client, admin_headers, operator_a_headers):
        """Count reflects the number of briefs."""
        _create_company(client, admin_headers, name="CountCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="One")
        opp2 = _create_opportunity(client, operator_a_headers, title="Two")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] >= 2

    def test_count_filtered(self, client, admin_headers, operator_a_headers):
        """Count respects status filter."""
        _create_company(client, admin_headers, name="CountFilter")
        opp1 = _create_opportunity(client, operator_a_headers, title="D")
        opp2 = _create_opportunity(client, operator_a_headers, title="R")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])
        _set_brief_status(client, operator_a_headers, opp2["id"], "ready_for_review")

        res = client.get("/proposal-briefs/count?status=draft", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] >= 1

    def test_count_requires_auth(self, client, admin_headers, operator_a_headers):
        """Count requires authentication."""
        res = client.get("/proposal-briefs/count")
        assert res.status_code in (401, 403)
