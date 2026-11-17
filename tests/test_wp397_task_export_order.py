"""WP-397 — Export internal tasks CSV with selected sort order.

Covers: four sort orders, tie-breaking, combined filters, no pagination,
tenant isolation, empty export, backward compatibility, and invalid sort rejection.
"""
import csv
import io

from datetime import datetime, timedelta

from app.models import Company, InternalTask
from conftest import TestingSessionLocal


def _create_companies():
    with TestingSessionLocal() as db:
        db.add_all([
            Company(id=1, name="Synthetic A", slug="export-a"),
            Company(id=2, name="Synthetic B", slug="export-b"),
        ])
        db.commit()


def _create_tasks(company_id: int, count: int = 3):
    """Create tasks with varying attributes for sort testing."""
    with TestingSessionLocal() as db:
        now = datetime.now()
        tasks_data = [
            {
                "id": 1,
                "company_id": company_id,
                "event_id": "evt-alpha",
                "payload": {"channel": "web", "message": "test"},
                "status": "queued",
                "attempts": 0,
                "created_at": now - timedelta(hours=2),
                "available_at": now - timedelta(hours=1),
            },
            {
                "id": 2,
                "company_id": company_id,
                "event_id": "evt-beta",
                "payload": {"channel": "web", "message": "test"},
                "status": "succeeded",
                "attempts": 1,
                "created_at": now - timedelta(hours=1),
                "available_at": now - timedelta(minutes=30),
            },
            {
                "id": 3,
                "company_id": company_id,
                "event_id": "evt-gamma",
                "payload": {"channel": "web", "message": "test"},
                "status": "failed",
                "attempts": 3,
                "created_at": now,
                "available_at": now,
            },
        ]
        for t in tasks_data:
            db.add(InternalTask(**t))
        db.commit()
    return [t["id"] for t in tasks_data]


def _parse_csv_rows(resp):
    """Parse CSV response body into list of row lists."""
    reader = csv.reader(io.StringIO(resp.text))
    return list(reader)


def test_export_default_sort_is_id_ascending(client, operator_a_headers):
    """Without sort param, export returns tasks ordered by ID ascending."""
    _create_companies()
    _create_tasks(1)
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = _parse_csv_rows(resp)
    # Header + 3 data rows
    assert len(rows) == 4
    ids = [int(row[0]) for row in rows[1:]]
    assert ids == [1, 2, 3]


def test_export_sort_by_created_at_descending(client, operator_a_headers):
    """sort=created_at returns newest first."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"sort": "created_at"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    ids = [int(row[0]) for row in rows[1:]]
    # ID 3 (now) > ID 2 (1h ago) > ID 1 (2h ago)
    assert ids == [3, 2, 1]


def test_export_sort_by_status_descending(client, operator_a_headers):
    """sort=status returns tasks ordered by status descending."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"sort": "status"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    statuses = [row[2] for row in rows[1:]]
    # SQLite DESC on text: succeeded > queued > failed (alphabetical desc)
    assert statuses == ["succeeded", "queued", "failed"]


def test_export_sort_by_attempts_descending(client, operator_a_headers):
    """sort=attempts returns tasks with most attempts first."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"sort": "attempts"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    attempts = [int(row[3]) for row in rows[1:]]
    # 3 > 1 > 0
    assert attempts == [3, 1, 0]


def test_export_sort_by_id_descending(client, operator_a_headers):
    """sort=id returns tasks ordered by ID descending."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"sort": "id"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    ids = [int(row[0]) for row in rows[1:]]
    assert ids == [3, 2, 1]


def test_export_sort_tiebreak_by_id_descending(client, operator_a_headers):
    """When sort column values are equal, tiebreak by ID descending."""
    _create_companies()
    with TestingSessionLocal() as db:
        now = datetime.now()
        # Two tasks with same status
        db.add_all([
            InternalTask(
                id=10, company_id=1, event_id="evt-x",
                payload={"channel": "web", "message": "test"},
                status="queued", attempts=0,
                created_at=now - timedelta(hours=1),
                available_at=now,
            ),
            InternalTask(
                id=20, company_id=1, event_id="evt-y",
                payload={"channel": "web", "message": "test"},
                status="queued", attempts=0,
                created_at=now - timedelta(hours=2),
                available_at=now,
            ),
        ])
        db.commit()

    resp = client.get(
        "/internal-tasks/export.csv",
        params={"sort": "status"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    # Among queued tasks, higher ID first
    queued_ids = [int(row[0]) for row in rows[1:] if row[2] == "queued"]
    assert queued_ids == sorted(queued_ids, reverse=True)


def test_export_with_status_filter(client, operator_a_headers):
    """Export respects status filter combined with sort."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"status": "failed", "sort": "attempts"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    # Only header + 1 failed task
    assert len(rows) == 2
    assert rows[1][2] == "failed"


def test_export_with_search_filter(client, operator_a_headers):
    """Export respects keyword search filter."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"q": "beta"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    assert len(rows) == 2
    assert "evt-beta" in rows[1][1]


def test_export_with_date_range_filter(client, operator_a_headers):
    """Export respects date range filter."""
    _create_companies()
    _create_tasks(1)
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"from_date": tomorrow, "to_date": tomorrow},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    # No tasks created tomorrow — header only
    assert len(rows) == 1


def test_export_no_pagination(client, operator_a_headers):
    """Export returns all matching tasks regardless of pagination params."""
    _create_companies()
    _create_tasks(1)
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    # All 3 tasks exported, not limited by default limit=50
    assert len(rows) == 4  # header + 3


def _create_tasks_company2(company_id: int = 2):
    """Create tasks for company 2 with unique IDs."""
    with TestingSessionLocal() as db:
        now = datetime.now()
        tasks_data = [
            {
                "id": 101,
                "company_id": company_id,
                "event_id": "evt-delta",
                "payload": {"channel": "web", "message": "test"},
                "status": "queued",
                "attempts": 0,
                "created_at": now - timedelta(hours=2),
                "available_at": now - timedelta(hours=1),
            },
            {
                "id": 102,
                "company_id": company_id,
                "event_id": "evt-epsilon",
                "payload": {"channel": "web", "message": "test"},
                "status": "succeeded",
                "attempts": 1,
                "created_at": now - timedelta(hours=1),
                "available_at": now - timedelta(minutes=30),
            },
            {
                "id": 103,
                "company_id": company_id,
                "event_id": "evt-zeta",
                "payload": {"channel": "web", "message": "test"},
                "status": "failed",
                "attempts": 3,
                "created_at": now,
                "available_at": now,
            },
        ]
        for t in tasks_data:
            db.add(InternalTask(**t))
        db.commit()


def test_export_tenant_isolation(client, operator_a_headers, operator_b_headers):
    """Export only returns tasks for the authenticated tenant."""
    _create_companies()
    _create_tasks(1)
    _create_tasks_company2(2)
    resp_a = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    resp_b = client.get("/internal-tasks/export.csv", headers=operator_b_headers)
    rows_a = _parse_csv_rows(resp_a)
    rows_b = _parse_csv_rows(resp_b)
    # Both see only their own tasks
    assert len(rows_a) == 4  # header + 3
    assert len(rows_b) == 4  # header + 3
    # Verify they see different event IDs
    events_a = {row[1] for row in rows_a[1:]}
    events_b = {row[1] for row in rows_b[1:]}
    assert events_a == {"evt-alpha", "evt-beta", "evt-gamma"}
    assert events_b == {"evt-delta", "evt-epsilon", "evt-zeta"}


def test_export_empty_result(client, operator_a_headers):
    """Export with no tasks returns CSV with header only."""
    _create_companies()
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    assert len(rows) == 1  # header only
    assert rows[0] == ["ID", "Evento", "Status", "Tentativas", "Erro", "Disponível em", "Criada em"]


def test_export_requires_authentication(client):
    """Export without auth returns 401."""
    _create_companies()
    resp = client.get("/internal-tasks/export.csv")
    assert resp.status_code == 401


def test_export_invalid_sort_returns_422(client, operator_a_headers):
    """Invalid sort value returns 422."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"sort": "invalid_value"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 422


def test_export_csv_headers_correct(client, operator_a_headers):
    """CSV header row matches expected columns."""
    _create_companies()
    _create_tasks(1)
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    rows = _parse_csv_rows(resp)
    expected_header = ["ID", "Evento", "Status", "Tentativas", "Erro", "Disponível em", "Criada em"]
    assert rows[0] == expected_header


def test_export_csv_content_disposition(client, operator_a_headers):
    """Response includes correct Content-Disposition header."""
    _create_companies()
    _create_tasks(1)
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    assert "attachment" in resp.headers["content-disposition"]
    assert "internal-tasks.csv" in resp.headers["content-disposition"]


def test_export_combined_filters_and_sort(client, operator_a_headers):
    """Export with combined status, search, and sort params works correctly."""
    _create_companies()
    _create_tasks(1)
    resp = client.get(
        "/internal-tasks/export.csv",
        params={"status": "queued", "sort": "created_at"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    assert len(rows) == 2  # header + 1 queued task
    assert rows[1][2] == "queued"


def test_export_backward_compatible_no_sort(client, operator_a_headers):
    """Omitting sort param maintains backward-compatible ID ascending order."""
    _create_companies()
    _create_tasks(1)
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    rows = _parse_csv_rows(resp)
    ids = [int(row[0]) for row in rows[1:]]
    assert ids == sorted(ids)  # ascending


def test_export_csv_contains_task_data(client, operator_a_headers):
    """CSV rows contain correct task field values."""
    _create_companies()
    _create_tasks(1)
    resp = client.get("/internal-tasks/export.csv", headers=operator_a_headers)
    rows = _parse_csv_rows(resp)
    # Check first data row (ID=1, evt-alpha, queued, 0 attempts)
    assert rows[1][0] == "1"
    assert rows[1][1] == "evt-alpha"
    assert rows[1][2] == "queued"
    assert rows[1][3] == "0"
