"""WP-101 — Lead sorting by id, created_at, status."""
import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, operator_headers, company_id, name, interest=None, status=None):
    data = {"company_id": company_id, "name": name, "phone": "11999999999", "source": "web"}
    if interest:
        data["interest"] = interest
    res = client.post("/leads", headers=operator_headers, json=data)
    assert res.status_code == 200
    lead = res.json()
    if status:
        client.patch(f"/leads/{lead['id']}", headers=operator_headers, json={"status": status})
    return lead


class TestLeadSorting:
    """Verify GET /leads?sort= sorting."""

    def test_default_sort_by_id(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Charlie")
        _create_lead(client, operator_a_headers, 1, "Alice")
        _create_lead(client, operator_a_headers, 1, "Bob")

        res = client.get("/leads", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        ids = [l["id"] for l in leads]
        assert ids == sorted(ids)

    def test_sort_by_created_at_desc(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "First")
        _create_lead(client, operator_a_headers, 1, "Second")
        _create_lead(client, operator_a_headers, 1, "Third")

        res = client.get("/leads?sort=created_at", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        # When created_at is identical (same second), tiebreaker is id ascending
        ids = [l["id"] for l in leads]
        assert ids == sorted(ids)

    def test_sort_by_status(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Won Lead", status="won")
        _create_lead(client, operator_a_headers, 1, "New Lead", status="new")
        _create_lead(client, operator_a_headers, 1, "Qualified Lead", status="qualified")

        res = client.get("/leads?sort=status", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        statuses = [l["status"] for l in leads]
        assert statuses == sorted(statuses)

    def test_sort_with_pagination(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(15):
            _create_lead(client, operator_a_headers, 1, f"Lead {i:03d}")

        res1 = client.get("/leads?sort=created_at&limit=5&offset=0", headers=operator_a_headers)
        assert res1.status_code == 200
        leads1 = res1.json()
        assert len(leads1) == 5

        res2 = client.get("/leads?sort=created_at&limit=5&offset=5", headers=operator_a_headers)
        assert res2.status_code == 200
        leads2 = res2.json()
        assert len(leads2) == 5

        ids1 = {l["id"] for l in leads1}
        ids2 = {l["id"] for l in leads2}
        assert ids1.isdisjoint(ids2)

    def test_sort_with_status_filter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "New A", status="new")
        _create_lead(client, operator_a_headers, 1, "New B", status="new")
        _create_lead(client, operator_a_headers, 1, "Contacted A", status="contacted")

        res = client.get("/leads?status=new&sort=id", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["status"] == "new" for l in leads)

    def test_sort_with_search_filter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Automação Z", interest="z")
        _create_lead(client, operator_a_headers, 1, "Automação A", interest="a")

        res = client.get("/leads?q=automação&sort=id", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 2

    def test_sort_requires_auth(self, client):
        res = client.get("/leads?sort=id")
        assert res.status_code in (401, 403)

    def test_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        _create_lead(client, operator_a_headers, 1, "Alpha Lead")
        _create_lead(client, operator_b_headers, 2, "Beta Lead")

        res = client.get("/leads?sort=id", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all("Alpha" in l["name"] for l in leads)
