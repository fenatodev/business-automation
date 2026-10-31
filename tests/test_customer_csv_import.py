"""WP-158 — Importação CSV de customers.

Testa POST /customers/import.csv com validação, deduplicação e tenant isolation.
"""

import csv
import io


class TestCustomerCsvImport:
    """Test CSV import of customers."""

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
        writer.writerow(["Nome", "Telefone", "E-mail"])
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")

    def test_import_valid_csv(self, client, admin_headers, operator_a_headers):
        """Valid CSV imports customers successfully."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Ana Silva", "11999990001", "ana@example.com"],
            ["Carlos Santos", "11999990002", "carlos@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0
        assert data["errors"] == 0

    def test_import_skips_duplicate_phone(self, client, admin_headers, operator_a_headers):
        """Duplicate phone numbers are skipped."""
        company = self._create_company(client, admin_headers)
        # Create a customer first
        client.post(
            "/customers",
            json={"company_id": company["id"], "name": "Existente", "phone": "11999990001"},
            headers=operator_a_headers,
        )

        csv_data = self._build_csv([
            ["Existente", "11999990001", "existente@example.com"],
            ["Novo", "11999990002", "novo@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_import_skips_duplicate_within_file(self, client, admin_headers, operator_a_headers):
        """Duplicate phone numbers within the same file are skipped."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Ana", "11999990001", "ana@example.com"],
            ["Ana Dup", "11999990001", "ana2@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    def test_import_errors_on_missing_name(self, client, admin_headers, operator_a_headers):
        """Rows with empty name are counted as errors."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["", "11999990001", "ana@example.com"],
            ["Valido", "11999990002", "valido@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["errors"] == 1

    def test_import_errors_on_missing_phone(self, client, admin_headers, operator_a_headers):
        """Rows with empty phone are counted as errors."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Sem Telefone", "", "sem@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
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
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 400

    def test_import_rejects_empty_file(self, client, admin_headers, operator_a_headers):
        """Empty CSV file is rejected."""
        company = self._create_company(client, admin_headers)
        csv_data = b""

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 400

    def test_import_requires_auth(self, client, admin_headers, operator_a_headers):
        """Import requires authentication."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Ana", "11999990001", "ana@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
        )
        assert resp.status_code in (401, 403)

    def test_import_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Imported customers belong to the operator's company only."""
        company_a = self._create_company(client, admin_headers)
        resp = client.post("/companies", json={
            "name": "Test Company B",
            "slug": "test-company-b",
        }, headers=admin_headers)
        assert resp.status_code == 200

        csv_data = self._build_csv([
            ["Ana", "11999990091", "ana@example.com"],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

        # Company B should have no customers
        resp = client.get("/customers", headers=operator_b_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_import_optional_email(self, client, admin_headers, operator_a_headers):
        """Email is optional; customers without email are imported."""
        company = self._create_company(client, admin_headers)
        csv_data = self._build_csv([
            ["Ana", "11999990001", ""],
        ])

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

        # Verify the customer was created
        resp = client.get("/customers", headers=operator_a_headers)
        assert resp.status_code == 200
        customers = resp.json()
        assert len(customers) == 1
        assert customers[0]["name"] == "Ana"
        assert customers[0]["email"] is None

    def test_import_handles_utf8_bom(self, client, admin_headers, operator_a_headers):
        """CSV with UTF-8 BOM is handled correctly."""
        company = self._create_company(client, admin_headers)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Nome", "Telefone", "E-mail"])
        writer.writerow(["Ana", "11999990001", "ana@example.com"])
        csv_data = ("\uFEFF" + output.getvalue()).encode("utf-8")

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

    def test_import_max_rows(self, client, admin_headers, operator_a_headers):
        """Only first 500 rows are processed."""
        company = self._create_company(client, admin_headers)
        rows = []
        for i in range(510):
            rows.append([f"Lead {i}", f"1199999{i:04d}", f"lead{i}@example.com"])
        csv_data = self._build_csv(rows)

        resp = client.post(
            "/customers/import.csv",
            files={"file": ("customers.csv", csv_data, "text/csv")},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 500
        assert data["total_processed"] == 500
