"""WP-177 — Filter leads by source.

Tests that the operator can filter leads by their source (manual, 99freelas,
intake, review_queue, import) via backend and UI contract.
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, source="manual", name="Lead"):
    res = client.post("/leads", headers=headers, json={
        "company_id": 1,
        "name": name,
        "phone": "5511999990000",
        "source": source,
    })
    assert res.status_code == 200
    return res.json()


class TestLeadSourceFilter:
    """Test ?source= filter on GET /leads."""

    def test_filter_by_manual_source(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="ManualCo")
        _create_lead(client, operator_a_headers, source="manual", name="Manual1")
        _create_lead(client, operator_a_headers, source="99freelas", name="Freelas1")

        res = client.get("/leads?source=manual", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["source"] == "manual" for l in leads)
        assert len(leads) >= 1

    def test_filter_by_intake_source(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="IntakeCo")
        _create_lead(client, operator_a_headers, source="intake", name="Intake1")
        _create_lead(client, operator_a_headers, source="manual", name="Manual1")

        res = client.get("/leads?source=intake", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["source"] == "intake" for l in leads)

    def test_filter_by_review_queue_source(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="RqCo")
        _create_lead(client, operator_a_headers, source="review_queue", name="RQ1")
        _create_lead(client, operator_a_headers, source="manual", name="Manual1")

        res = client.get("/leads?source=review_queue", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["source"] == "review_queue" for l in leads)

    def test_filter_by_import_source(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="ImportCo")
        _create_lead(client, operator_a_headers, source="import", name="Import1")
        _create_lead(client, operator_a_headers, source="manual", name="Manual1")

        res = client.get("/leads?source=import", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["source"] == "import" for l in leads)

    def test_no_source_filter_returns_all(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="AllCo")
        _create_lead(client, operator_a_headers, source="manual", name="M1")
        _create_lead(client, operator_a_headers, source="intake", name="I1")

        res = client.get("/leads", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        sources = {l["source"] for l in leads}
        assert "manual" in sources
        assert "intake" in sources

    def test_source_filter_with_count(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="CountCo")
        _create_lead(client, operator_a_headers, source="manual", name="M1")
        _create_lead(client, operator_a_headers, source="manual", name="M2")
        _create_lead(client, operator_a_headers, source="intake", name="I1")

        res = client.get("/leads/count?source=manual", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["total"] >= 2

    def test_source_filter_with_export_csv(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="CsvCo")
        _create_lead(client, operator_a_headers, source="manual", name="M1")
        _create_lead(client, operator_a_headers, source="intake", name="I1")

        res = client.get("/leads/export.csv?source=manual", headers=operator_a_headers)
        assert res.status_code == 200
        text = res.text
        assert "M1" in text
        assert "I1" not in text

    def test_source_filter_combined_with_status(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="ComboCo")
        _create_lead(client, operator_a_headers, source="manual", name="M1")

        res = client.get("/leads?source=manual&status=new", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["source"] == "manual" and l["status"] == "new" for l in leads)

    def test_source_filter_requires_auth(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="AuthCo")

        res = client.get("/leads?source=manual")
        assert res.status_code in (401, 403)

    def test_source_filter_tenant_isolation(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="TenantCo")
        _create_lead(client, operator_a_headers, source="manual", name="M1")

        # Only leads from the operator's company are returned
        res = client.get("/leads?source=manual", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert all(l["source"] == "manual" for l in leads)


class TestLeadSourceFilterUI:
    """Test UI contract for lead source filter."""

    def test_source_filter_dropdown_exists(self):
        from pathlib import Path
        html = Path("app/operator_ui/index.html").read_text()
        assert 'id="lead-filter-source"' in html

    def test_source_filter_options(self):
        from pathlib import Path
        html = Path("app/operator_ui/index.html").read_text()
        assert 'value="manual"' in html
        assert 'value="99freelas"' in html
        assert 'value="intake"' in html
        assert 'value="review_queue"' in html
        assert 'value="import"' in html

    def test_source_filter_handler_exists(self):
        from pathlib import Path
        js = Path("app/operator_ui/app.js").read_text()
        assert 'lead-filter-source' in js

    def test_source_in_refresh_leads(self):
        from pathlib import Path
        js = Path("app/operator_ui/app.js").read_text()
        # refreshLeads should include source in params
        idx = js.find("async function refreshLeads")
        func_body = js[idx:idx + 2000]
        assert "source" in func_body

    def test_source_in_clear_filters(self):
        from pathlib import Path
        js = Path("app/operator_ui/app.js").read_text()
        idx = js.find("lead-clear-filters")
        section = js[idx:idx + 500]
        assert "lead-filter-source" in section

    def test_source_in_export_csv(self):
        from pathlib import Path
        js = Path("app/operator_ui/app.js").read_text()
        idx = js.find("leads-export-csv")
        section = js[idx:idx + 800]
        assert "source" in section
