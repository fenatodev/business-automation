"""Filtered task CSV exports follow the operator's selected ordering."""
import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.models import Company, InternalTask
from conftest import TestingSessionLocal


@pytest.fixture
def export_tasks():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="export-a"),
                    Company(id=2, name="Synthetic B", slug="export-b")])
        db.flush()
        for task_id, tenant, status, attempts, day, event in [
            (1, 1, "queued", 2, 3, "match-one"),
            (2, 1, "failed", 1, 2, "match-two"),
            (3, 1, "queued", 2, 3, "match-three"),
            (4, 1, "queued", 3, 4, "other"),
            (5, 2, "queued", 3, 3, "match-other-tenant"),
        ]:
            db.add(InternalTask(id=task_id, company_id=tenant, event_id=event,
                                payload={"message": "synthetic private payload"},
                                status=status, attempts=attempts,
                                available_at=datetime(2026, 11, day),
                                created_at=datetime(2026, 11, day)))
        db.commit()


def csv_ids(response):
    assert response.status_code == 200
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [
    ("id", [3, 2, 1]), ("created_at", [3, 1, 2]),
    ("status", [3, 1, 2]), ("attempts", [3, 1, 2]),
])
def test_export_order_matches_filtered_list(client, operator_a_headers, export_tasks, sort, expected):
    params = {"sort": sort, "q": "match", "from_date": "2026-11-02", "to_date": "2026-11-03"}
    listing = client.get("/internal-tasks/", params={**params, "limit": 1}, headers=operator_a_headers)
    assert listing.status_code == 200
    response = client.get("/internal-tasks/export.csv", params=params, headers=operator_a_headers)
    assert csv_ids(response) == expected
    assert listing.json()[0]["id"] == expected[0]
    assert "synthetic private payload" not in response.text


def test_export_order_combines_status_and_empty_filters(client, operator_a_headers, export_tasks):
    response = client.get("/internal-tasks/export.csv?sort=attempts&status=queued&q=match", headers=operator_a_headers)
    assert csv_ids(response) == [3, 1]
    response = client.get("/internal-tasks/export.csv?sort=id&q=missing", headers=operator_a_headers)
    assert csv_ids(response) == []


def test_export_without_sort_preserves_ascending_ids(client, operator_a_headers, export_tasks):
    assert csv_ids(client.get("/internal-tasks/export.csv", headers=operator_a_headers)) == [1, 2, 3, 4]


def test_export_rejects_unknown_sort(client, operator_a_headers):
    assert client.get("/internal-tasks/export.csv?sort=payload", headers=operator_a_headers).status_code == 422


def test_export_button_passes_current_sort_and_filters():
    subprocess.run(["node", "tests/js/task_export_order.cjs"], cwd=Path(__file__).resolve().parents[1], check=True)
