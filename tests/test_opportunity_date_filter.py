"""WP-149 — Filtro de data em oportunidades.

Testa os parâmetros from_date e to_date em GET /opportunities,
GET /opportunities/count e GET /opportunities/export.csv.
Usa comparação de strings ISO 8601 compatível com SQLite e PostgreSQL.
"""
from datetime import datetime, timezone


class TestOpportunityDateFilter:
    """Test date range filtering on opportunities."""

    def _create_company(self, client, headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_opportunity(self, client, company_id, headers, captured_at=None):
        resp = client.post("/opportunities", json={
            "company_id": company_id,
            "source": "manual",
            "external_url": f"https://example.com/opp-{captured_at or 'now'}",
            "title": "Test Opportunity",
            "description": "Test description",
            "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_from_date_filters_created_at(self, client, admin_headers, operator_a_headers):
        """from_date filters opportunities created on or after the date."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-01-01T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-06-15T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-12-31T10:00:00Z")

        resp = client.get(
            "/opportunities?from_date=2026-06-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2

    def test_to_date_filters_created_at(self, client, admin_headers, operator_a_headers):
        """to_date filters opportunities created on or before the date."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-01-01T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-06-15T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-12-31T10:00:00Z")

        resp = client.get(
            "/opportunities?to_date=2026-06-30",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2

    def test_from_and_to_date_range(self, client, admin_headers, operator_a_headers):
        """Both from_date and to_date work together to create a range."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-01-01T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-06-15T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-12-31T10:00:00Z")

        resp = client.get(
            "/opportunities?from_date=2026-06-01&to_date=2026-06-30",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert "2026-06-15" in results[0]["captured_at"]

    def test_date_filter_with_count(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects date filters."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-01-01T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-06-15T10:00:00Z")

        resp = client.get(
            "/opportunities/count?from_date=2026-06-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_date_filter_with_export_csv(self, client, admin_headers, operator_a_headers):
        """Export CSV respects date filters."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-01-01T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-06-15T10:00:00Z")

        resp = client.get(
            "/opportunities/export.csv?from_date=2026-06-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        # Header + 1 data row
        assert len(lines) == 2

    def test_date_filter_combined_with_other_filters(self, client, admin_headers, operator_a_headers):
        """Date filter works with next_action and search filters."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-06-15T10:00:00Z")

        resp = client.get(
            "/opportunities?from_date=2026-06-01&next_action=pending",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_empty_date_filter_returns_all(self, client, admin_headers, operator_a_headers):
        """No date params returns all opportunities."""
        company = self._create_company(client, admin_headers)

        self._create_opportunity(client, company["id"], operator_a_headers, "2026-01-01T10:00:00Z")
        self._create_opportunity(client, company["id"], operator_a_headers, "2026-12-31T10:00:00Z")

        resp = client.get(
            "/opportunities",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_date_filter_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Date filter respects tenant isolation."""
        company_a = self._create_company(client, admin_headers)
        self._create_opportunity(client, company_a["id"], operator_a_headers, "2026-06-15T10:00:00Z")

        company_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b",
        }, headers=admin_headers).json()
        self._create_opportunity(client, company_b["id"], operator_b_headers, "2026-06-15T10:00:00Z")

        resp = client.get(
            "/opportunities?from_date=2026-06-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        for opp in resp.json():
            assert opp["company_id"] == company_a["id"]
