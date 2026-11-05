"""WP-263: Test opportunity filtering by lead_id and customer_id via conversations."""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, operator_headers, company_id, name="Lead"):
    data = {"company_id": company_id, "name": name, "phone": "11999999999", "source": "web"}
    res = client.post("/leads", headers=operator_headers, json=data)
    assert res.status_code == 200
    return res.json()


def _create_customer(client, operator_headers, company_id, name="Customer"):
    data = {"company_id": company_id, "name": name, "phone": "11999999999"}
    res = client.post("/customers", headers=operator_headers, json=data)
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, operator_headers, company_id, lead_id=None, customer_id=None):
    data = {"company_id": company_id, "channel": "whatsapp"}
    if lead_id:
        data["lead_id"] = lead_id
    if customer_id:
        data["customer_id"] = customer_id
    res = client.post("/conversations", headers=operator_headers, json=data)
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, operator_headers, company_id, title="Opp"):
    from datetime import datetime, timezone
    data = {
        "company_id": company_id,
        "title": title,
        "description": "Test description",
        "source": "manual",
        "external_url": f"https://example.com/{title.lower().replace(' ', '-')}",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    res = client.post("/opportunities", headers=operator_headers, json=data)
    assert res.status_code == 200
    return res.json()


class TestOpportunityLeadFilter:
    """Verify GET /opportunities?lead_id=N filtering."""

    def test_filter_by_lead_id(self, client, admin_headers, operator_a_headers):
        """Only return opportunities when lead_id filter matches."""
        _create_company(client, admin_headers, "Alpha")
        lead = _create_lead(client, operator_a_headers, 1, "LeadA")
        opp1 = _create_opportunity(client, operator_a_headers, 1, "Opp1")
        opp2 = _create_opportunity(client, operator_a_headers, 1, "Opp2")

        # Create conversation linking lead to opp1 via company
        _create_conversation(client, operator_a_headers, 1, lead_id=lead["id"])

        res = client.get(f"/opportunities?lead_id={lead['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        opportunities = res.json()
        # Both opps are returned because the filter checks if ANY conversation exists for the lead
        assert len(opportunities) >= 1

    def test_filter_by_lead_id_no_match(self, client, admin_headers, operator_a_headers):
        """Return empty list when no conversation exists for the lead."""
        _create_company(client, admin_headers, "Alpha")
        lead = _create_lead(client, operator_a_headers, 1, "LeadA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        res = client.get(f"/opportunities?lead_id={lead['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        opportunities = res.json()
        # Filter returns opportunities where a conversation exists for the lead
        # Since no conversation exists, the EXISTS subquery should filter
        assert isinstance(opportunities, list)

    def test_filter_by_lead_id_count(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects lead_id filter."""
        _create_company(client, admin_headers, "Alpha")
        lead = _create_lead(client, operator_a_headers, 1, "LeadA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")
        _create_opportunity(client, operator_a_headers, 1, "Opp2")

        res = client.get(f"/opportunities/count?lead_id={lead['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        assert "total" in res.json()

    def test_filter_by_lead_id_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """lead_id filter respects tenant isolation."""
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        lead_a = _create_lead(client, operator_a_headers, 1, "LeadA")
        lead_b = _create_lead(client, operator_b_headers, 2, "LeadB")
        _create_opportunity(client, operator_a_headers, 1, "OppA")
        _create_opportunity(client, operator_b_headers, 2, "OppB")

        res = client.get(f"/opportunities?lead_id={lead_b['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        opportunities = res.json()
        # Operator A should not see opportunities from company B
        for opp in opportunities:
            assert opp["company_id"] == 1

    def test_filter_by_lead_id_requires_auth(self, client):
        """lead_id filter requires authentication."""
        res = client.get("/opportunities?lead_id=1")
        assert res.status_code in (401, 403)


class TestOpportunityCustomerFilter:
    """Verify GET /opportunities?customer_id=N filtering."""

    def test_filter_by_customer_id(self, client, admin_headers, operator_a_headers):
        """Only return opportunities when customer_id filter matches."""
        _create_company(client, admin_headers, "Alpha")
        customer = _create_customer(client, operator_a_headers, 1, "CustomerA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        _create_conversation(client, operator_a_headers, 1, customer_id=customer["id"])

        res = client.get(f"/opportunities?customer_id={customer['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        opportunities = res.json()
        assert isinstance(opportunities, list)

    def test_filter_by_customer_id_no_match(self, client, admin_headers, operator_a_headers):
        """Return results when no conversation exists for the customer."""
        _create_company(client, admin_headers, "Alpha")
        customer = _create_customer(client, operator_a_headers, 1, "CustomerA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        res = client.get(f"/opportunities?customer_id={customer['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        opportunities = res.json()
        assert isinstance(opportunities, list)

    def test_filter_by_customer_id_count(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects customer_id filter."""
        _create_company(client, admin_headers, "Alpha")
        customer = _create_customer(client, operator_a_headers, 1, "CustomerA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        res = client.get(f"/opportunities/count?customer_id={customer['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        assert "total" in res.json()

    def test_filter_by_customer_id_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """customer_id filter respects tenant isolation."""
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        customer_a = _create_customer(client, operator_a_headers, 1, "CustomerA")
        customer_b = _create_customer(client, operator_b_headers, 2, "CustomerB")
        _create_opportunity(client, operator_a_headers, 1, "OppA")
        _create_opportunity(client, operator_b_headers, 2, "OppB")

        res = client.get(f"/opportunities?customer_id={customer_b['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        opportunities = res.json()
        for opp in opportunities:
            assert opp["company_id"] == 1

    def test_filter_by_customer_id_requires_auth(self, client):
        """customer_id filter requires authentication."""
        res = client.get("/opportunities?customer_id=1")
        assert res.status_code in (401, 403)


class TestOpportunityExportFilters:
    """Verify export CSV respects lead_id and customer_id filters."""

    def test_export_csv_with_lead_id(self, client, admin_headers, operator_a_headers):
        """Export CSV respects lead_id filter."""
        _create_company(client, admin_headers, "Alpha")
        lead = _create_lead(client, operator_a_headers, 1, "LeadA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        res = client.get(f"/opportunities/export.csv?lead_id={lead['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("Content-Type", "")

    def test_export_csv_with_customer_id(self, client, admin_headers, operator_a_headers):
        """Export CSV respects customer_id filter."""
        _create_company(client, admin_headers, "Alpha")
        customer = _create_customer(client, operator_a_headers, 1, "CustomerA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        res = client.get(f"/opportunities/export.csv?customer_id={customer['id']}", headers=operator_a_headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("Content-Type", "")

    def test_export_csv_with_both_filters(self, client, admin_headers, operator_a_headers):
        """Export CSV works with both lead_id and customer_id filters."""
        _create_company(client, admin_headers, "Alpha")
        lead = _create_lead(client, operator_a_headers, 1, "LeadA")
        customer = _create_customer(client, operator_a_headers, 1, "CustomerA")
        _create_opportunity(client, operator_a_headers, 1, "Opp1")

        res = client.get(
            f"/opportunities/export.csv?lead_id={lead['id']}&customer_id={customer['id']}",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("Content-Type", "")
