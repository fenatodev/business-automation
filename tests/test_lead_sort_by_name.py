"""WP-261: Test lead name sorting in list_leads."""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, operator_headers, company_id, name, phone=None):
    data = {"company_id": company_id, "name": name, "phone": phone or "11999999999", "source": "web"}
    res = client.post("/leads", headers=operator_headers, json=data)
    assert res.status_code == 200
    return res.json()


class TestLeadSortByName:
    """Verify GET /leads?sort=name sorting."""

    def test_sort_by_name_ascending(self, client, admin_headers, operator_a_headers):
        """Leads sorted by name should return Alpha, Middle, Zebra."""
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Zebra", "111")
        _create_lead(client, operator_a_headers, 1, "Alpha", "222")
        _create_lead(client, operator_a_headers, 1, "Middle", "333")

        res = client.get("/leads?sort=name", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 3
        assert leads[0]["name"] == "Alpha"
        assert leads[1]["name"] == "Middle"
        assert leads[2]["name"] == "Zebra"

    def test_sort_by_name_with_status_filter(self, client, admin_headers, operator_a_headers):
        """Name sort works with status filter."""
        _create_company(client, admin_headers, "Alpha")
        lead_a = _create_lead(client, operator_a_headers, 1, "Alpha", "111")
        _create_lead(client, operator_a_headers, 1, "Zebra", "222")
        client.patch(f"/leads/{lead_a['id']}", headers=operator_a_headers, json={"status": "contacted"})

        res = client.get("/leads?sort=name&status=contacted", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 1
        assert leads[0]["name"] == "Alpha"

    def test_sort_by_name_with_search(self, client, admin_headers, operator_a_headers):
        """Name sort works with keyword search."""
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Alpha", "111")
        _create_lead(client, operator_a_headers, 1, "Middle", "222")
        _create_lead(client, operator_a_headers, 1, "Zebra", "333")

        res = client.get("/leads?sort=name&q=le", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        names = [l["name"] for l in leads]
        assert names == sorted(names)

    def test_sort_by_name_respects_pagination(self, client, admin_headers, operator_a_headers):
        """Name sort respects limit/offset."""
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Zebra", "111")
        _create_lead(client, operator_a_headers, 1, "Alpha", "222")
        _create_lead(client, operator_a_headers, 1, "Middle", "333")

        res = client.get("/leads?sort=name&limit=2&offset=1", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 2
        assert leads[0]["name"] == "Middle"
        assert leads[1]["name"] == "Zebra"

    def test_sort_by_name_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Name sort returns only tenant leads."""
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        _create_lead(client, operator_a_headers, 1, "Zebra", "111")
        _create_lead(client, operator_a_headers, 1, "Alpha", "222")
        _create_lead(client, operator_b_headers, 2, "AAA", "999")

        res = client.get("/leads?sort=name", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        names = [l["name"] for l in leads]
        assert "AAA" not in names
        assert len(leads) == 2

    def test_sort_by_name_requires_auth(self, client):
        """Name sort requires authentication."""
        res = client.get("/leads?sort=name")
        assert res.status_code in (401, 403)
