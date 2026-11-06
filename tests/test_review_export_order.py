"""Review queue export preserves the operator's selected order and filters."""
import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.models import Company, ReviewQueueItem
from conftest import TestingSessionLocal


@pytest.fixture
def export_items():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="review-export-a"),
                    Company(id=2, name="Synthetic B", slug="review-export-b")])
        db.flush()
        for item_id, tenant, message, day, status, intent in [
            (1, 1, "Zulu match", 2, "pending", "inquiry"),
            (2, 1, "Alpha match", 3, "approved", "inquiry"),
            (3, 1, "Alpha match", 3, "pending", "inquiry"),
            (4, 1, "Other", 4, "pending", "other"),
            (5, 2, "Alpha match", 3, "pending", "inquiry"),
        ]:
            db.add(ReviewQueueItem(id=item_id, company_id=tenant, message=message,
                        event_id=f"synthetic-{item_id}", status=status, intent=intent, channel="web",
                        created_at=datetime(2026, 11, day)))
        db.commit()


def csv_ids(response):
    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=review-queue.csv"
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [
    ("id", [1, 2, 3]), ("created_at", [2, 3, 1]), ("status", [2, 1, 3]),
])
def test_export_order_filters_and_all_pages(client, operator_a_headers, export_items, sort, expected):
    params = {"sort": sort, "q": "match",
              "from_date": "2026-11-02", "to_date": "2026-11-03"}
    listing = client.get("/review-queue/", params={**params, "status": "pending", "limit": 1}, headers=operator_a_headers)
    assert listing.status_code == 200
    response = client.get("/review-queue/export.csv", params=params, headers=operator_a_headers)
    assert csv_ids(response) == expected
    assert listing.json()[0]["id"] == next(item_id for item_id in expected if item_id != 2)
    response = client.get("/review-queue/export.csv", params={**params, "status": "pending"}, headers=operator_a_headers)
    assert csv_ids(response) == [item_id for item_id in expected if item_id != 2]


def test_export_default_empty_and_other_tenant(client, operator_a_headers, operator_b_headers, export_items):
    assert csv_ids(client.get("/review-queue/export.csv", headers=operator_a_headers)) == [1, 2, 3, 4]
    assert csv_ids(client.get("/review-queue/export.csv?sort=status&q=missing", headers=operator_a_headers)) == []
    assert csv_ids(client.get("/review-queue/export.csv?sort=status", headers=operator_b_headers)) == [5]


def test_export_rejects_unknown_sort(client, operator_a_headers):
    assert client.get("/review-queue/export.csv?sort=phone", headers=operator_a_headers).status_code == 422


def test_export_button_passes_current_order_and_filters():
    subprocess.run(["node", "tests/js/review_export_order.cjs"],
                   cwd=Path(__file__).resolve().parents[1], check=True)
