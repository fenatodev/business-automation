"""WP-159 — Importação CSV de oportunidades.

Testa POST /opportunities/import.csv com validação, deduplicação e tenant isolation.
"""

import csv
import io


class TestOpportunityCsvImport:
    """Test CSV import of opportunities."""

    def _create_company(self, client, admin_headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=admin_headers)
        assert resp.status_code == 200
        return resp.json()

    def _build_csv(self, rows):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Título", "Descrição", "URL", "Orçamento", "Prazo", "Requisitos"])
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")

    def test_import_valid_csv(self, client, admin_headers, operator_a_headers):
        """Valid CSV imports opportunities successfully."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Site E-commerce", "Loja online de roupas", "https://example.com/1", "R$ 15000", "2026-12-31", "WordPress"],
            ["App Mobile", "App de delivery", "https://example.com/2", "R$ 30000", "2027-03-31", "React Native"],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0
        assert data["errors"] == 0

    def test_import_skips_duplicate_url(self, client, admin_headers, operator_a_headers):
        """Duplicate external_url values are skipped."""
        company = self._create_company(client, admin_headers)
        # Create an opportunity first
        client.post(
            "/opportunities",
            json={
                "company_id": company["id"],
                "source": "manual",
                "external_url": "https://example.com/existing",
                "title": "Existente",
                "description": "Já existe",
                "captured_at": "2026-01-01T00:00:00",
            },
            headers=operator_a_headers,
        )

        csv_data = self._build_csv([
            ["Existente", "Já existe", "https://example.com/existing", "", "", ""],
            ["Novo", "Novo projeto", "https://example.com/new", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_import_skips_duplicate_within_file(self, client, admin_headers, operator_a_headers):
        """Duplicate URLs within the same file are skipped."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Projeto A", "Desc A", "https://example.com/dup", "", "", ""],
            ["Projeto A dup", "Desc A dup", "https://example.com/dup", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_import_errors_on_missing_title(self, client, admin_headers, operator_a_headers):
        """Rows with empty title are counted as errors."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["", "Sem título", "https://example.com/1", "", "", ""],
            ["Válido", "Descrição válida", "https://example.com/2", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["errors"] == 1

    def test_import_errors_on_missing_description(self, client, admin_headers, operator_a_headers):
        """Rows with empty description are counted as errors."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Sem descrição", "", "https://example.com/1", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 0
        assert data["errors"] == 1

    def test_import_rejects_missing_columns(self, client, admin_headers, operator_a_headers):
        """CSV without required columns is rejected."""
        company = self._create_company(client, admin_headers)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ColunaErrada"])
        writer.writerow(["valor"])
        csv_data = output.getvalue().encode("utf-8")

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 400

    def test_import_rejects_empty_file(self, client, admin_headers, operator_a_headers):
        """Empty CSV file is rejected."""
        company = self._create_company(client, admin_headers)
        csv_data = b""

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 400

    def test_import_requires_auth(self, client, admin_headers, operator_a_headers):
        """Import requires authentication."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Projeto", "Descrição", "https://example.com/1", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
        )
        assert resp.status_code in (401, 403)

    def test_import_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Imported opportunities belong to the operator's company only."""
        company_a = self._create_company(client, admin_headers)
        resp = client.post("/companies", json={
            "name": "Test Company B",
            "slug": "test-company-b",
        }, headers=admin_headers)
        assert resp.status_code == 200

        csv_data = self._build_csv([
            ["Projeto", "Descrição", "https://example.com/iso", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

        # Company B should have no opportunities
        resp = client.get("/opportunities", headers=operator_b_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_import_generates_url_if_missing(self, client, admin_headers, operator_a_headers):
        """Missing URL is auto-generated."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Projeto", "Descrição", "", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

        # Verify the opportunity was created
        resp = client.get("/opportunities", headers=operator_a_headers)
        assert resp.status_code == 200
        opps = resp.json()
        assert len(opps) == 1
        assert opps[0]["source"] == "import"
        assert opps[0]["next_action"] == "pending"

    def test_import_optional_fields(self, client, admin_headers, operator_a_headers):
        """Budget, deadline, requirements are optional."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Projeto", "Descrição", "https://example.com/1", "", "", ""],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

        resp = client.get("/opportunities", headers=operator_a_headers)
        opps = resp.json()
        assert opps[0]["budget"] is None
        assert opps[0]["deadline"] is None
        assert opps[0]["requirements"] is None

    def test_import_with_all_fields(self, client, admin_headers, operator_a_headers):
        """All fields are imported correctly."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Projeto", "Descrição", "https://example.com/1", "R$ 10000", "2026-12-31", "Python"],
        ])

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

        resp = client.get("/opportunities", headers=operator_a_headers)
        opps = resp.json()
        assert opps[0]["budget"] == "R$ 10000"
        assert opps[0]["deadline"] == "2026-12-31"
        assert opps[0]["requirements"] == "Python"

    def test_import_max_rows(self, client, admin_headers, operator_a_headers):
        """Only first 500 rows are processed."""
        company = self._create_company(client, admin_headers)
        rows = []
        for i in range(510):
            rows.append([f"Projeto {i}", f"Desc {i}", f"https://example.com/{i}", "", "", ""])
        csv_data = self._build_csv(rows)

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 500
        assert data["total_processed"] == 500

    def test_import_handles_utf8_bom(self, client, admin_headers, operator_a_headers):
        """CSV with UTF-8 BOM is handled correctly."""
        company = self._create_company(client, admin_headers)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Título", "Descrição", "URL", "Orçamento", "Prazo", "Requisitos"])
        writer.writerow(["Projeto", "Descrição", "https://example.com/1", "", "", ""])
        csv_data = ("\uFEFF" + output.getvalue()).encode("utf-8")

        resp = client.post(
            "/opportunities/import.csv",
            files={"file": ("opportunities.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1
