"""Lead export preserves the operator's selected order and filters."""
import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.models import Company, Lead
from conftest import TestingSessionLocal


@pytest.fixture
def export_leads():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="lead-export-a"),
                    Company(id=2, name="Synthetic B", slug="lead-export-b")])
        db.flush()
        for lead_id, tenant, name, day, status, source in [
            (1, 1, "Zulu match", 2, "new", "manual"),
            (2, 1, "Alpha match", 3, "qualified", "manual"),
            (3, 1, "Alpha match", 3, "new", "manual"),
            (4, 1, "Other", 4, "new", "import"),
            (5, 2, "Alpha match", 3, "new", "manual"),
        ]:
            db.add(Lead(id=lead_id, company_id=tenant, name=name,
                        phone=f"synthetic-{lead_id}", status=status, source=source,
                        created_at=datetime(2026, 11, day)))
        db.commit()


def csv_ids(response):
    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=leads.csv"
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [
    ("id", [1, 2, 3]), ("name", [2, 3, 1]),
    ("created_at", [2, 3, 1]), ("status", [1, 3, 2]),
])
def test_export_order_filters_and_all_pages(client, operator_a_headers, export_leads, sort, expected):
    params = {"sort": sort, "source": "manual", "q": "match",
              "from_date": "2026-11-02", "to_date": "2026-11-03"}
    listing = client.get("/leads", params={**params, "limit": 1}, headers=operator_a_headers)
    assert listing.status_code == 200
    response = client.get("/leads/export.csv", params=params, headers=operator_a_headers)
    assert csv_ids(response) == expected
    assert listing.json()[0]["id"] == expected[0]
    response = client.get("/leads/export.csv", params={**params, "status": "new"}, headers=operator_a_headers)
    assert csv_ids(response) == [lead_id for lead_id in expected if lead_id != 2]


def test_export_default_empty_and_other_tenant(client, operator_a_headers, operator_b_headers, export_leads):
    assert csv_ids(client.get("/leads/export.csv", headers=operator_a_headers)) == [1, 2, 3, 4]
    assert csv_ids(client.get("/leads/export.csv?sort=name&q=missing", headers=operator_a_headers)) == []
    assert csv_ids(client.get("/leads/export.csv?sort=name", headers=operator_b_headers)) == [5]


def test_export_rejects_unknown_sort(client, operator_a_headers):
    assert client.get("/leads/export.csv?sort=phone", headers=operator_a_headers).status_code == 422


def test_export_button_passes_current_order_and_filters():
    subprocess.run(["node", "tests/js/lead_export_order.cjs"],
                   cwd=Path(__file__).resolve().parents[1], check=True)
