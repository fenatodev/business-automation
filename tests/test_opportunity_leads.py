"""WP-144 — Leads relacionados à oportunidade.

Testa o endpoint GET /opportunities/{id}/leads que retorna
leads da mesma company que a oportunidade, com tenant isolation.
"""
from datetime import datetime, timezone


class TestOpportunityLeads:
    """Test opportunity-related leads endpoint."""

    def _create_company(self, client, headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_opportunity(self, client, company_id, headers):
        resp = client.post("/opportunities", json={
            "company_id": company_id,
            "source": "manual",
            "external_url": "https://example.com/opp",
            "title": "Test Opportunity",
            "description": "Test description",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_lead(self, client, company_id, headers):
        resp = client.post("/leads", json={
            "company_id": company_id,
            "name": "Test Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_get_leads_returns_empty_list(self, client, admin_headers, operator_a_headers):
        """GET /opportunities/{id}/leads returns empty list when no leads exist."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/leads",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_leads_returns_company_leads(self, client, admin_headers, operator_a_headers):
        """Endpoint returns leads belonging to the same company."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)
        self._create_lead(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/leads",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        leads = resp.json()
        assert len(leads) >= 1

    def test_get_leads_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A sees only their company's leads, not company B's."""
        company_a = self._create_company(client, admin_headers)
        assert company_a["id"] == 1
        opp_a = self._create_opportunity(client, company_a["id"], operator_a_headers)

        # Create lead for company A
        self._create_lead(client, company_a["id"], operator_a_headers)

        # Create company B and lead
        company_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b",
        }, headers=admin_headers).json()
        self._create_lead(client, company_b["id"], operator_b_headers)

        # Operator A should only see leads from company A
        resp = client.get(
            f"/opportunities/{opp_a['id']}/leads",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        for lead in resp.json():
            assert lead["company_id"] == company_a["id"]

    def test_get_leads_requires_auth(self, client, admin_headers, operator_a_headers):
        """Endpoint requires authentication."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(f"/opportunities/{opp['id']}/leads")
        assert resp.status_code in (401, 403)

    def test_get_leads_404_for_unknown_opportunity(self, client, admin_headers, operator_a_headers):
        """Returns 404 when opportunity doesn't exist."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers)

        resp = client.get(
            "/opportunities/99999/leads",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404

    def test_get_leads_404_for_other_tenant_opportunity(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Returns 404 when opportunity belongs to another tenant."""
        company_a = self._create_company(client, admin_headers)
        company_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b-2",
        }, headers=admin_headers).json()
        opp_b = self._create_opportunity(client, company_b["id"], operator_b_headers)

        resp = client.get(
            f"/opportunities/{opp_b['id']}/leads",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404

    def test_leads_ordered_by_id_desc(self, client, admin_headers, operator_a_headers):
        """Leads are returned ordered by ID descending."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        lead1 = self._create_lead(client, company["id"], operator_a_headers)
        lead2 = self._create_lead(client, company["id"], operator_a_headers)
        assert lead2["id"] > lead1["id"]

        resp = client.get(
            f"/opportunities/{opp['id']}/leads",
            headers=operator_a_headers,
        )
        leads = resp.json()
        ids = [l["id"] for l in leads]
        assert ids == sorted(ids, reverse=True)

    def test_leads_limited_to_50(self, client, admin_headers, operator_a_headers):
        """Endpoint limits results to 50 leads."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        for _ in range(55):
            self._create_lead(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/leads",
            headers=operator_a_headers,
        )
        leads = resp.json()
        assert len(leads) == 50
