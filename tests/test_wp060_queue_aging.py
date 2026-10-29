"""WP-060: tenant-scoped aging metric, no customer data exposure."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import update
from app.models import ReviewQueueItem
from tests.test_commercial_pipeline_e2e import _synthetic_trigger
from conftest import TestingSessionLocal


def test_aging_requires_auth(client):
    assert client.get("/review-queue/aging").status_code == 401


def test_aging_isolated_pending_only(client, admin_headers, operator_a_headers, operator_b_headers):
    for n in (1, 2):
        assert client.post("/companies", json={"name": f"Aging {n}", "slug": f"aging-{n}"}, headers=admin_headers).status_code == 200
    a = client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id="aging-a"), headers=operator_a_headers)
    b = client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id="aging-b"), headers=operator_b_headers)
    assert a.status_code == b.status_code == 201
    with TestingSessionLocal() as db_session:
        db_session.execute(update(ReviewQueueItem).where(ReviewQueueItem.id.in_([a.json()["id"], b.json()["id"]])).values(created_at=datetime.now(timezone.utc) - timedelta(hours=25)))
        db_session.commit()
    assert client.get("/review-queue/aging", headers=operator_a_headers).json() == {"older_than_hours": 24, "overdue_pending": 1}
    assert client.get("/review-queue/aging", headers=operator_b_headers).json()["overdue_pending"] == 1
    assert client.patch(f"/review-queue/{a.json()['id']}/decision", json={"decision": "approve"}, headers=operator_a_headers).status_code == 200
    assert client.get("/review-queue/aging", headers=operator_a_headers).json()["overdue_pending"] == 0
    assert client.get("/review-queue/aging", headers=operator_b_headers).json()["overdue_pending"] == 1
