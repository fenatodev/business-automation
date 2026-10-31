"""WP-095 — Opportunity sort and pagination tests."""
from datetime import datetime, timezone

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, operator_headers, company_id, title="Test Opp", description="Test desc"):
    now = datetime.now(timezone.utc).isoformat()
    res = client.post(
        "/opportunities",
        headers=operator_headers,
        json={
            "source": "99freelas",
            "external_url": f"https://example.com/{title}-{company_id}",
            "title": title,
            "description": description,
            "captured_at": now,
        },
    )
    assert res.status_code == 200
    return res.json()


class TestOpportunitySort:
    """Verify sort parameter in GET /opportunities."""

    def test_sort_by_id_default(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "C", "C desc")
        _create_opportunity(client, operator_a_headers, 1, "A", "A desc")
        _create_opportunity(client, operator_a_headers, 1, "B", "B desc")
        res = client.get("/opportunities", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        ids = [o["id"] for o in data]
        assert ids == sorted(ids)

    def test_sort_by_created_at_desc(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        # Create with different captured_at timestamps
        _create_opportunity(client, operator_a_headers, 1, "First", "First desc")
        _create_opportunity(client, operator_a_headers, 1, "Second", "Second desc")
        res = client.get("/opportunities?sort=created_at", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        # Most recent created_at first — second created has higher ID and later timestamp
        assert data[0]["id"] > data[1]["id"]

    def test_sort_by_next_action(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        opp1 = _create_opportunity(client, operator_a_headers, 1, "Pending", "P")
        opp2 = _create_opportunity(client, operator_a_headers, 1, "Done", "D")
        # Change one to done
        client.patch(
            f"/opportunities/{opp2['id']}/triage",
            headers=operator_a_headers,
            json={"next_action": "done"},
        )
        res = client.get("/opportunities?sort=next_action", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        # pending < done alphabetically
        actions = [o["next_action"] for o in data]
        assert actions == sorted(actions)


class TestOpportunityPagination:
    """Verify limit/offset pagination in GET /opportunities."""

    def test_limit(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(5):
            _create_opportunity(client, operator_a_headers, 1, f"Opp{i}", f"Desc{i}")
        res = client.get("/opportunities?limit=3", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 3

    def test_offset(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(5):
            _create_opportunity(client, operator_a_headers, 1, f"Opp{i}", f"Desc{i}")
        res = client.get("/opportunities?limit=2&offset=2", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        # Should return items at offset 2 and 3
        assert data[0]["id"] >= 3

    def test_limit_max_100(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.get("/opportunities?limit=101", headers=operator_a_headers)
        assert res.status_code == 422

    def test_offset_negative_rejected(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.get("/opportunities?offset=-1", headers=operator_a_headers)
        assert res.status_code == 422

    def test_pagination_with_search(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "Alpha project", "A")
        _create_opportunity(client, operator_a_headers, 1, "Beta project", "B")
        _create_opportunity(client, operator_a_headers, 1, "Gamma project", "G")
        res = client.get("/opportunities?q=project&limit=2", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2

    def test_pagination_with_exclude_archived(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        opp1 = _create_opportunity(client, operator_a_headers, 1, "Active", "A")
        opp2 = _create_opportunity(client, operator_a_headers, 1, "Done", "D")
        client.patch(
            f"/opportunities/{opp2['id']}/triage",
            headers=operator_a_headers,
            json={"next_action": "done"},
        )
        res = client.get("/opportunities?exclude_archived=true&limit=10", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["title"] == "Active"


class TestOpportunityCount:
    """Verify GET /opportunities/count endpoint."""

    def test_count_all(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "A", "A")
        _create_opportunity(client, operator_a_headers, 1, "B", "B")
        res = client.get("/opportunities/count", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2

    def test_count_exclude_archived(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        opp1 = _create_opportunity(client, operator_a_headers, 1, "Active", "A")
        opp2 = _create_opportunity(client, operator_a_headers, 1, "Done", "D")
        client.patch(
            f"/opportunities/{opp2['id']}/triage",
            headers=operator_a_headers,
            json={"next_action": "done"},
        )
        res = client.get("/opportunities/count?exclude_archived=true", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1

    def test_count_with_search(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "Alpha project", "A")
        _create_opportunity(client, operator_a_headers, 1, "Beta project", "B")
        _create_opportunity(client, operator_a_headers, 1, "Gamma", "G")
        res = client.get("/opportunities/count?q=project", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2

    def test_count_empty(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.get("/opportunities/count", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0

    def test_count_requires_auth(self, client):
        res = client.get("/opportunities/count")
        assert res.status_code in (401, 403)

    def test_count_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        _create_opportunity(client, operator_a_headers, 1, "A", "A")
        _create_opportunity(client, operator_a_headers, 1, "B", "B")
        res = client.get("/opportunities/count", headers=operator_b_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
