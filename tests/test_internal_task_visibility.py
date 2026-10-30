"""Operational read endpoints preserve tenant and privacy boundaries."""
from datetime import timedelta

import pytest

from app.models import Company, InternalTask
from app.services import internal_tasks as tasks
from conftest import TestingSessionLocal


@pytest.fixture
def task_rows():
    now = tasks.utcnow()
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="visibility-a"),
                    Company(id=2, name="Synthetic B", slug="visibility-b")])
        db.flush()
        ids = []
        for company_id in (1, 2):
            for index, state in enumerate(("queued", "queued", "running", "succeeded", "failed")):
                row = InternalTask(company_id=company_id, event_id=f"event-{index}",
                                   payload={"message": "private synthetic content"}, status=state,
                                   available_at=now - timedelta(hours=25) if index == 0 else now + timedelta(hours=1),
                                   lease_until=now - timedelta(seconds=1) if state == "running" else None,
                                   created_at=now, claim_token="private-worker-token")
                db.add(row)
                db.flush()
                if company_id == 1:
                    ids.append(row.id)
        db.commit()
    return list(reversed(ids))


def test_pagination_filters_and_privacy(task_rows, client, operator_a_headers):
    first = client.get("/internal-tasks/?limit=2", headers=operator_a_headers)
    second = client.get("/internal-tasks/?limit=2&offset=2", headers=operator_a_headers)
    last = client.get("/internal-tasks/?limit=2&offset=4", headers=operator_a_headers)
    assert first.status_code == second.status_code == last.status_code == 200
    rows = first.json() + second.json() + last.json()
    assert [row["id"] for row in rows] == task_rows
    assert all(not {"payload", "message", "claim_token"} & row.keys() for row in rows)
    assert client.get("/internal-tasks/?offset=50", headers=operator_a_headers).json() == []
    failed = client.get("/internal-tasks/?status=failed", headers=operator_a_headers).json()
    assert len(failed) == 1 and failed[0]["status"] == "failed"


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "status=unknown"])
def test_invalid_query_rejected(client, operator_a_headers, query):
    assert client.get(f"/internal-tasks/?{query}", headers=operator_a_headers).status_code == 422


def test_summary_excludes_other_tenant_and_retry_wait(task_rows, client, operator_a_headers):
    response = client.get("/internal-tasks/summary", headers=operator_a_headers)
    assert response.status_code == 200
    assert response.json() == {"queued": 2, "running": 1, "succeeded": 1, "failed": 1,
                               "overdue_queued": 1, "expired_running": 1}


def test_empty_summary(client, operator_a_headers):
    assert set(client.get("/internal-tasks/summary", headers=operator_a_headers).json().values()) == {0}


@pytest.mark.parametrize("path", ["/internal-tasks/", "/internal-tasks/summary"])
def test_read_requires_operator(client, admin_headers, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=admin_headers).status_code == 403
