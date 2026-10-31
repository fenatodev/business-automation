"""WP-152 — Filtro de data em leads.

Testa os parâmetros from_date e to_date em GET /leads,
GET /leads/count e GET /leads/export.csv.
"""


class TestLeadDateFilter:
    """Test date range filtering on leads endpoints."""

    def _create_company(self, client, admin_headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=admin_headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_lead(self, client, company_id, operator_headers, name="Test Lead"):
        resp = client.post("/leads", json={
            "company_id": company_id,
            "name": name,
            "phone": "11999999999",
            "source": "site",
        }, headers=operator_headers)
        assert resp.status_code == 200
        return resp.json()

    def test_from_date_filters(self, client, admin_headers, operator_a_headers):
        """from_date filters leads created on or after the date."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")
        self._create_lead(client, company["id"], operator_a_headers, "Lead2")

        # from_date in the future returns 0
        resp = client.get(
            "/leads?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # from_date in the past returns all
        resp = client.get(
            "/leads?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_to_date_filters(self, client, admin_headers, operator_a_headers):
        """to_date filters leads created on or before the date."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")
        self._create_lead(client, company["id"], operator_a_headers, "Lead2")

        # to_date in the past returns 0
        resp = client.get(
            "/leads?to_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # to_date in the future returns all
        resp = client.get(
            "/leads?to_date=2099-12-31",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_from_and_to_date_range(self, client, admin_headers, operator_a_headers):
        """Both from_date and to_date work together."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")

        # Range that includes now
        resp = client.get(
            "/leads?from_date=2000-01-01&to_date=2099-12-31",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Range that excludes now
        resp = client.get(
            "/leads?from_date=2000-01-01&to_date=2000-06-30",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_count_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """GET /leads/count respects from_date/to_date."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")
        self._create_lead(client, company["id"], operator_a_headers, "Lead2")

        resp = client.get(
            "/leads/count?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

        resp = client.get(
            "/leads/count?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_export_csv_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """GET /leads/export.csv respects from_date/to_date."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")

        resp = client.get(
            "/leads/export.csv?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row

        resp = client.get(
            "/leads/export.csv?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_date_filter_with_status_filter(self, client, admin_headers, operator_a_headers):
        """Date filter works combined with status filter."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")

        resp = client.get(
            "/leads?from_date=2000-01-01&status=new",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = client.get(
            "/leads?from_date=2000-01-01&status=qualified",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_date_filter_with_search(self, client, admin_headers, operator_a_headers):
        """Date filter works combined with search query."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Alpha")
        self._create_lead(client, company["id"], operator_a_headers, "Beta")

        resp = client.get(
            "/leads?from_date=2000-01-01&q=Alpha",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Alpha"

    def test_no_date_filter_returns_all(self, client, admin_headers, operator_a_headers):
        """No date params returns all leads."""
        company = self._create_company(client, admin_headers)
        self._create_lead(client, company["id"], operator_a_headers, "Lead1")
        self._create_lead(client, company["id"], operator_a_headers, "Lead2")

        resp = client.get(
            "/leads",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
