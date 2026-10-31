"""WP-151 — Filtro de data em conversas.

Testa os parâmetros from_date e to_date em GET /conversations,
GET /conversations/count e GET /conversations/export.csv.
"""


class TestConversationDateFilter:
    """Test date range filtering on conversations."""

    def _create_company(self, client, admin_headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=admin_headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_lead(self, client, company_id, operator_headers):
        resp = client.post("/leads", json={
            "company_id": company_id,
            "name": "Test Lead",
            "phone": "11999999999",
            "source": "site",
        }, headers=operator_headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_conversation(self, client, company_id, lead_id, operator_headers):
        resp = client.post("/conversations", json={
            "company_id": company_id,
            "channel": "whatsapp",
            "lead_id": lead_id,
        }, headers=operator_headers)
        assert resp.status_code == 200
        return resp.json()

    def test_from_date_filters(self, client, admin_headers, operator_a_headers):
        """from_date filters conversations created on or after the date."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        # All created now, so from_date in the future returns 0
        resp = client.get(
            f"/companies/{company['id']}/conversations?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # from_date in the past returns all
        resp = client.get(
            f"/companies/{company['id']}/conversations?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_to_date_filters(self, client, admin_headers, operator_a_headers):
        """to_date filters conversations created on or before the date."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        # to_date in the past returns 0
        resp = client.get(
            f"/companies/{company['id']}/conversations?to_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # to_date in the future returns all
        resp = client.get(
            f"/companies/{company['id']}/conversations?to_date=2099-12-31",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_from_and_to_date_range(self, client, admin_headers, operator_a_headers):
        """Both from_date and to_date work together."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        # Range that includes now
        resp = client.get(
            f"/companies/{company['id']}/conversations?from_date=2000-01-01&to_date=2099-12-31",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Range that excludes now
        resp = client.get(
            f"/companies/{company['id']}/conversations?from_date=2000-01-01&to_date=2000-06-30",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_date_filter_with_count(self, client, admin_headers, operator_a_headers):
        """Count endpoint respects date filters."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        resp = client.get(
            f"/companies/{company['id']}/conversations/count?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

        resp = client.get(
            f"/companies/{company['id']}/conversations/count?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_date_filter_with_export_csv(self, client, admin_headers, operator_a_headers):
        """Export CSV respects date filters."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        resp = client.get(
            f"/companies/{company['id']}/conversations/export.csv?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row

        resp = client.get(
            f"/companies/{company['id']}/conversations/export.csv?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_date_filter_combined_with_other_filters(self, client, admin_headers, operator_a_headers):
        """Date filter works with channel and status filters."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        resp = client.get(
            f"/companies/{company['id']}/conversations?from_date=2000-01-01&channel=whatsapp",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = client.get(
            f"/companies/{company['id']}/conversations?from_date=2000-01-01&channel=telegram",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_no_date_filter_returns_all(self, client, admin_headers, operator_a_headers):
        """No date params returns all conversations."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)

        resp = client.get(
            f"/companies/{company['id']}/conversations",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
