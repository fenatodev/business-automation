"""WP-153 — Filtro de data em customers.

Testa os parâmetros from_date e to_date em GET /customers,
GET /customers/count e GET /customers/export.csv.
"""


class TestCustomerDateFilter:
    """Test date range filtering on customers endpoints."""

    def _create_company(self, client, admin_headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=admin_headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_customer(self, client, company_id, operator_headers, name="Test Customer"):
        resp = client.post("/customers", json={
            "company_id": company_id,
            "name": name,
            "phone": "11999999999",
        }, headers=operator_headers)
        assert resp.status_code == 200
        return resp.json()

    def test_from_date_filters(self, client, admin_headers, operator_a_headers):
        """from_date filters customers created on or after the date."""
        company = self._create_company(client, admin_headers)
        self._create_customer(client, company["id"], operator_a_headers, "C1")
        self._create_customer(client, company["id"], operator_a_headers, "C2")

        resp = client.get(
            "/customers?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        resp = client.get(
            "/customers?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_to_date_filters(self, client, admin_headers, operator_a_headers):
        """to_date filters customers created on or before the date."""
        company = self._create_company(client, admin_headers)
        self._create_customer(client, company["id"], operator_a_headers, "C1")

        resp = client.get(
            "/customers?to_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        resp = client.get(
            "/customers?to_date=2099-12-31",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_count_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """GET /customers/count respects from_date/to_date."""
        company = self._create_company(client, admin_headers)
        self._create_customer(client, company["id"], operator_a_headers, "C1")
        self._create_customer(client, company["id"], operator_a_headers, "C2")

        resp = client.get(
            "/customers/count?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

        resp = client.get(
            "/customers/count?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_export_csv_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """GET /customers/export.csv respects from_date/to_date."""
        company = self._create_company(client, admin_headers)
        self._create_customer(client, company["id"], operator_a_headers, "C1")

        resp = client.get(
            "/customers/export.csv?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row

        resp = client.get(
            "/customers/export.csv?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_date_filter_with_search(self, client, admin_headers, operator_a_headers):
        """Date filter works combined with search query."""
        company = self._create_company(client, admin_headers)
        self._create_customer(client, company["id"], operator_a_headers, "Alpha")
        self._create_customer(client, company["id"], operator_a_headers, "Beta")

        resp = client.get(
            "/customers?from_date=2000-01-01&q=Alpha",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Alpha"

    def test_no_date_filter_returns_all(self, client, admin_headers, operator_a_headers):
        """No date params returns all customers."""
        company = self._create_company(client, admin_headers)
        self._create_customer(client, company["id"], operator_a_headers, "C1")
        self._create_customer(client, company["id"], operator_a_headers, "C2")

        resp = client.get(
            "/customers",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
