"""WP-155 — Filtro de data em internal tasks.

Testa os parâmetros from_date e to_date em GET /internal-tasks/,
GET /internal-tasks/count e GET /internal-tasks/export.csv.
"""


class TestInternalTaskDateFilter:
    """Test date range filtering on internal tasks endpoints."""

    def _create_company(self, client, admin_headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=admin_headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_task(self, client, company_id, operator_headers, event_id="test-task"):
        resp = client.post("/internal-tasks", json={
            "event_id": event_id,
            "message": "Test task",
            "channel": "web",
        }, headers=operator_headers)
        assert resp.status_code == 202
        return resp.json()

    def test_from_date_filters(self, client, admin_headers, operator_a_headers):
        """from_date filters tasks created on or after the date."""
        company = self._create_company(client, admin_headers)
        self._create_task(client, company["id"], operator_a_headers, "task-1")
        self._create_task(client, company["id"], operator_a_headers, "task-2")

        # from_date in the future returns 0
        resp = client.get(
            "/internal-tasks?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # from_date in the past returns all
        resp = client.get(
            "/internal-tasks?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_to_date_filters(self, client, admin_headers, operator_a_headers):
        """to_date filters tasks created on or before the date."""
        company = self._create_company(client, admin_headers)
        self._create_task(client, company["id"], operator_a_headers, "task-3")

        # to_date in the past returns 0
        resp = client.get(
            "/internal-tasks?to_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # to_date in the future returns all
        resp = client.get(
            "/internal-tasks?to_date=2099-12-31",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_count_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """GET /internal-tasks/count respects from_date/to_date."""
        company = self._create_company(client, admin_headers)
        self._create_task(client, company["id"], operator_a_headers, "task-4")
        self._create_task(client, company["id"], operator_a_headers, "task-5")

        resp = client.get(
            "/internal-tasks/count?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == 2

        resp = client.get(
            "/internal-tasks/count?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == 0

    def test_export_csv_respects_date_filter(self, client, admin_headers, operator_a_headers):
        """GET /internal-tasks/export.csv respects from_date/to_date."""
        company = self._create_company(client, admin_headers)
        self._create_task(client, company["id"], operator_a_headers, "task-6")

        resp = client.get(
            "/internal-tasks/export.csv?from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row

        resp = client.get(
            "/internal-tasks/export.csv?from_date=2099-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_date_filter_with_status_filter(self, client, admin_headers, operator_a_headers):
        """Date filter works combined with status filter."""
        company = self._create_company(client, admin_headers)
        self._create_task(client, company["id"], operator_a_headers, "task-7")

        resp = client.get(
            "/internal-tasks?status=queued&from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = client.get(
            "/internal-tasks?status=failed&from_date=2000-01-01",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_no_date_filter_returns_all(self, client, admin_headers, operator_a_headers):
        """No date params returns all tasks."""
        company = self._create_company(client, admin_headers)
        self._create_task(client, company["id"], operator_a_headers, "task-8")
        self._create_task(client, company["id"], operator_a_headers, "task-9")

        resp = client.get(
            "/internal-tasks",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
