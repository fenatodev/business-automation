"""WP-100 — Lead pagination with limit/offset and count endpoint."""
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


class TestLeadPagination:
    """Verify GET /leads with limit/offset pagination."""

    def test_default_pagination_returns_50(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(55):
            _create_lead(client, operator_a_headers, 1, f"Lead {i:03d}")

        res = client.get("/leads", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 50

    def test_limit_parameter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(30):
            _create_lead(client, operator_a_headers, 1, f"Lead {i:03d}")

        res = client.get("/leads?limit=10", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 10

    def test_offset_parameter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(20):
            _create_lead(client, operator_a_headers, 1, f"Lead {i:03d}")

        res1 = client.get("/leads?limit=10&offset=0", headers=operator_a_headers)
        assert res1.status_code == 200
        leads1 = res1.json()
        assert len(leads1) == 10

        res2 = client.get("/leads?limit=10&offset=10", headers=operator_a_headers)
        assert res2.status_code == 200
        leads2 = res2.json()
        assert len(leads2) == 10

        ids1 = {l["id"] for l in leads1}
        ids2 = {l["id"] for l in leads2}
        assert ids1.isdisjoint(ids2)

    def test_limit_max_100(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(150):
            _create_lead(client, operator_a_headers, 1, f"Lead {i:03d}")

        res = client.get("/leads?limit=100", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 100

    def test_limit_over_100_rejected(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.get("/leads?limit=101", headers=operator_a_headers)
        assert res.status_code == 422

    def test_offset_beyond_total(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Only Lead")

        res = client.get("/leads?limit=10&offset=100", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 0

    def test_pagination_with_status_filter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(15):
            _create_lead(client, operator_a_headers, 1, f"New Lead {i}", status="new")
        for i in range(10):
            _create_lead(client, operator_a_headers, 1, f"Contacted Lead {i}", status="contacted")

        res = client.get("/leads?status=new&limit=5&offset=0", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 5
        assert all(l["status"] == "new" for l in leads)

        res2 = client.get("/leads?status=new&limit=5&offset=5", headers=operator_a_headers)
        assert res2.status_code == 200
        leads2 = res2.json()
        assert len(leads2) == 5

    def test_pagination_with_search_filter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(10):
            _create_lead(client, operator_a_headers, 1, f"Automação {i}", interest="automação industrial")
        for i in range(10):
            _create_lead(client, operator_a_headers, 1, f"Outro {i}", interest="algo diferente")

        res = client.get("/leads?q=automação&limit=5", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 5
        for lead in leads:
            assert "automação" in (lead["name"] or "").lower() or "automação" in (lead["interest"] or "").lower()

    def test_pagination_requires_auth(self, client):
        res = client.get("/leads?limit=10")
        assert res.status_code in (401, 403)

    def test_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        for i in range(10):
            _create_lead(client, operator_a_headers, 1, f"Alpha Lead {i}")
        for i in range(10):
            _create_lead(client, operator_b_headers, 2, f"Beta Lead {i}")

        res_a = client.get("/leads?limit=50", headers=operator_a_headers)
        assert res_a.status_code == 200
        leads_a = res_a.json()
        assert all("Alpha" in l["name"] for l in leads_a)

        res_b = client.get("/leads?limit=50", headers=operator_b_headers)
        assert res_b.status_code == 200
        leads_b = res_b.json()
        assert all("Beta" in l["name"] for l in leads_b)


class TestLeadCount:
    """Verify GET /leads/count endpoint."""

    def test_count_all_leads(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(25):
            _create_lead(client, operator_a_headers, 1, f"Lead {i:03d}")

        res = client.get("/leads/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 25

    def test_count_with_status_filter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for i in range(10):
            _create_lead(client, operator_a_headers, 1, f"New {i}", status="new")
        for i in range(5):
            _create_lead(client, operator_a_headers, 1, f"Contacted {i}", status="contacted")

        res = client.get("/leads/count?status=new", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 10

        res2 = client.get("/leads/count?status=contacted", headers=operator_a_headers)
        assert res2.status_code == 200
        assert res2.json()["total"] == 5

    def test_count_with_search_filter(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Automação Loja", interest="automação")
        _create_lead(client, operator_a_headers, 1, "ERP Integration", interest="erp")
        _create_lead(client, operator_a_headers, 1, "Automação Fábrica", interest="fábrica")

        res = client.get("/leads/count?q=automação", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 2

    def test_count_empty(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")

        res = client.get("/leads/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_count_requires_auth(self, client):
        res = client.get("/leads/count")
        assert res.status_code in (401, 403)

    def test_count_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        for i in range(10):
            _create_lead(client, operator_a_headers, 1, f"Alpha {i}")
        for i in range(5):
            _create_lead(client, operator_b_headers, 2, f"Beta {i}")

        res_a = client.get("/leads/count", headers=operator_a_headers)
        assert res_a.json()["total"] == 10

        res_b = client.get("/leads/count", headers=operator_b_headers)
        assert res_b.json()["total"] == 5
