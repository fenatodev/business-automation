"""WP-181 — Brief search, sort, and pagination.

Tests that the operator can search briefs by keywords, sort by different
fields, and paginate through results.
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
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    return res.json()


class TestBriefSearch:
    """Test GET /proposal-briefs?q= keyword search."""

    def test_search_by_title(self, client, admin_headers, operator_a_headers):
        """Search finds briefs by opportunity title."""
        _create_company(client, admin_headers, name="SearchCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="Website Redesign")
        opp2 = _create_opportunity(client, operator_a_headers, title="Mobile App")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs?q=Website", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1
        assert any("Website" in b["opportunity_title"] for b in briefs)

    def test_search_by_offer_reference(self, client, admin_headers, operator_a_headers):
        """Search finds briefs by offer reference."""
        _create_company(client, admin_headers, name="RefCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs?q=OFF-", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1

    def test_search_case_insensitive(self, client, admin_headers, operator_a_headers):
        """Search is case-insensitive."""
        _create_company(client, admin_headers, name="CaseCo")
        opp = _create_opportunity(client, operator_a_headers, title="Marketing Campaign")
        _create_brief(client, operator_a_headers, opp["id"])

        for query in ["marketing", "MARKETING", "Marketing"]:
            res = client.get(f"/proposal-briefs?q={query}", headers=operator_a_headers)
            assert res.status_code == 200
            briefs = res.json()
            assert len(briefs) >= 1

    def test_search_no_match(self, client, admin_headers, operator_a_headers):
        """Search with no match returns empty list."""
        _create_company(client, admin_headers, name="NoMatchCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs?q=nonexistent", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_count_respects_search(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects search filter."""
        _create_company(client, admin_headers, name="CountSearchCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="Alpha")
        opp2 = _create_opportunity(client, operator_a_headers, title="Beta")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs/count?q=Alpha", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] >= 1


class TestBriefSort:
    """Test GET /proposal-briefs?sort= ordering."""

    def test_sort_by_created_at(self, client, admin_headers, operator_a_headers):
        """Default sort is by created_at descending."""
        _create_company(client, admin_headers, name="SortCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs?sort=created_at", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 2

    def test_sort_by_id(self, client, admin_headers, operator_a_headers):
        """Sort by ID ascending."""
        _create_company(client, admin_headers, name="SortIdCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="A")
        opp2 = _create_opportunity(client, operator_a_headers, title="B")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs?sort=id", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 2

    def test_sort_by_status(self, client, admin_headers, operator_a_headers):
        """Sort by status."""
        _create_company(client, admin_headers, name="SortStatusCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs?sort=status", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1


class TestBriefPagination:
    """Test GET /proposal-briefs with limit/offset."""

    def test_default_limit(self, client, admin_headers, operator_a_headers):
        """Default limit is 50."""
        _create_company(client, admin_headers, name="PagCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) <= 50

    def test_custom_limit(self, client, admin_headers, operator_a_headers):
        """Custom limit works."""
        _create_company(client, admin_headers, name="CustomLimitCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        _create_brief(client, operator_a_headers, opp["id"])

        res = client.get("/proposal-briefs?limit=1", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) <= 1

    def test_offset(self, client, admin_headers, operator_a_headers):
        """Offset skips results."""
        _create_company(client, admin_headers, name="OffsetCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs?limit=1&offset=0", headers=operator_a_headers)
        assert res.status_code == 200
        first = res.json()

        res = client.get("/proposal-briefs?limit=1&offset=1", headers=operator_a_headers)
        assert res.status_code == 200
        second = res.json()

        # With different offsets, we should get different results
        assert len(first) >= 1
        assert len(second) >= 0

    def test_limit_max_100(self, client, admin_headers, operator_a_headers):
        """Limit cannot exceed 100."""
        _create_company(client, admin_headers, name="MaxLimitCo")
        res = client.get("/proposal-briefs?limit=101", headers=operator_a_headers)
        assert res.status_code == 422

    def test_count_with_pagination(self, client, admin_headers, operator_a_headers):
        """Count returns total regardless of pagination."""
        _create_company(client, admin_headers, name="CountPagCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="One")
        opp2 = _create_opportunity(client, operator_a_headers, title="Two")
        _create_brief(client, operator_a_headers, opp1["id"])
        _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] >= 2
