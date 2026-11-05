"""Customer CSV follows the selected ordering across all filtered results."""
import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.models import Company, Customer
from conftest import TestingSessionLocal


@pytest.fixture
def export_customers():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="export-a"),
                    Company(id=2, name="Synthetic B", slug="export-b")])
        db.flush()
        for customer_id, tenant, name, day in [
            (1, 1, "Zulu match", 2), (2, 1, "Alpha match", 3),
            (3, 1, "Alpha match", 3), (4, 1, "Other", 4),
            (5, 2, "Alpha match", 3),
        ]:
            db.add(Customer(id=customer_id, company_id=tenant, name=name,
                            phone=f"synthetic-{customer_id}",
                            created_at=datetime(2026, 11, day)))
        db.commit()


def csv_ids(response):
    assert response.status_code == 200
    assert "attachment; filename=customers.csv" == response.headers["content-disposition"]
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [
    ("id", [1, 2, 3]), ("name", [2, 3, 1]), ("created_at", [2, 3, 1]),
])
def test_export_selected_order_and_filters(client, operator_a_headers, export_customers, sort, expected):
    params = {"sort": sort, "q": "match", "from_date": "2026-11-02", "to_date": "2026-11-03"}
    listing = client.get("/customers", params={**params, "limit": 1}, headers=operator_a_headers)
    assert listing.status_code == 200
    response = client.get("/customers/export.csv", params=params, headers=operator_a_headers)
    assert csv_ids(response) == expected
    assert listing.json()[0]["id"] == expected[0]


def test_export_default_order_and_empty_result(client, operator_a_headers, export_customers):
    assert csv_ids(client.get("/customers/export.csv", headers=operator_a_headers)) == [1, 2, 3, 4]
    assert csv_ids(client.get("/customers/export.csv?sort=name&q=missing", headers=operator_a_headers)) == []


def test_export_rejects_unknown_sort(client, operator_a_headers):
    assert client.get("/customers/export.csv?sort=email", headers=operator_a_headers).status_code == 422


def test_export_button_passes_current_sort_and_filters():
    subprocess.run(["node", "tests/js/customer_export_order.cjs"],
                   cwd=Path(__file__).resolve().parents[1], check=True)
