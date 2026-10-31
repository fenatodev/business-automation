"""Durability, fencing, retry and tenant contracts for internal-only tasks."""
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.models import Company, InternalTask, ReviewQueueItem
from app.schemas import ReviewQueueTrigger
from app.services import internal_tasks as tasks
from conftest import TestingSessionLocal


@pytest.fixture
def companies():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="task-a"),
                    Company(id=2, name="Synthetic B", slug="task-b")])
        db.commit()


def trigger(event="task-1"):
    return ReviewQueueTrigger(channel="web", message="Gostaria de automatizar processos", event_id=event)


def test_api_durable_result_and_dedup(companies, client, operator_a_headers, operator_b_headers, admin_headers):
    payload = trigger().model_dump()
    assert client.post("/internal-tasks/", json=payload).status_code == 401
    assert client.post("/internal-tasks/", json=payload, headers=admin_headers).status_code == 403
    first = client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
    assert first.status_code == 202
    task_id = first.json()["id"]
    assert first.json()["status"] == "queued"
    assert client.post("/internal-tasks/", json=payload, headers=operator_a_headers).json()["id"] == task_id
    assert client.post("/internal-tasks/", json={**payload, "message": "different"}, headers=operator_a_headers).status_code == 409
    assert client.post("/internal-tasks/", json={**payload, "company_id": 2}, headers=operator_a_headers).status_code == 422
    assert client.get(f"/internal-tasks/{task_id}", headers=operator_b_headers).status_code == 404
    assert client.get(f"/internal-tasks/{task_id}", headers=admin_headers).status_code == 403
    assert tasks.run_once(TestingSessionLocal, "Synthetic automation")
    assert not tasks.run_once(TestingSessionLocal, "Synthetic automation")
    body = client.get(f"/internal-tasks/{task_id}", headers=operator_a_headers).json()
    assert body["status"] == "succeeded"
    assert body["attempts"] == 1
    assert not {"payload", "claim_token", "message"} & body.keys()
    item = client.get(f"/review-queue/{body['result']['review_item_id']}", headers=operator_a_headers).json()
    assert item["status"] == "pending"
    assert client.post("/internal-tasks/", json=payload, headers=operator_b_headers).json()["id"] != task_id


def test_expired_claim_cannot_write_result(companies):
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
        now = tasks.utcnow()
        old = tasks.claim(db, now=now)
        assert tasks.claim(db, now=now) is None
        later = now + timedelta(seconds=61)
        assert tasks.recover_expired(db, now=later) == 1
        assert tasks.claim(db, now=later) is None  # recovery backoff
        new = tasks.claim(db, now=later + timedelta(seconds=3))
        assert old[1] != new[1]
        assert not tasks.execute_claim(db, *old, "synthetic", now=later)
        assert db.scalar(select(func.count()).select_from(ReviewQueueItem)) == 0
        assert tasks.execute_claim(db, *new, "synthetic", now=later + timedelta(seconds=4))
        assert tasks.get_task(db, task_id, 1).status == "succeeded"


def test_worker_failure_rolls_back_result_and_exhausts_retries(companies, monkeypatch):
    original = tasks.build_review_item
    def broken(*args):
        raise RuntimeError("private payload must not escape")
    monkeypatch.setattr(tasks, "build_review_item", broken)
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
    for attempt in range(1, 4):
        assert tasks.run_once(TestingSessionLocal, "synthetic")
        with TestingSessionLocal() as db:
            task = db.get(InternalTask, task_id)
            assert task.attempts == attempt
            assert task.status == ("failed" if attempt == 3 else "queued")
            assert task.error_code == "processing_failed"
            assert task.result is None
            assert db.scalar(select(func.count()).select_from(ReviewQueueItem)) == 0
            assert tasks.claim(db) is None
            task.available_at = tasks.utcnow() - timedelta(seconds=1)
            db.commit()
    monkeypatch.setattr(tasks, "build_review_item", original)
    assert not tasks.run_once(TestingSessionLocal, "synthetic")


def test_rollback_after_result_insert_is_atomic(companies, monkeypatch):
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
        claimed = tasks.claim(db)
        def fail_commit():
            raise RuntimeError("commit failure")
        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError):
            tasks.execute_claim(db, *claimed, "synthetic")
        db.rollback()
    with TestingSessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReviewQueueItem)) == 0
        assert db.get(InternalTask, task_id).status == "running"


def test_sync_result_reused(companies):
    from app.services.commercial_pipeline import triage_and_queue
    with TestingSessionLocal() as db:
        item_id = triage_and_queue(db, trigger(), 1, "synthetic").id
        task_id = tasks.enqueue(db, trigger(), 1).id
        claimed = tasks.claim(db)
        assert tasks.execute_claim(db, *claimed, "synthetic")
        assert db.get(InternalTask, task_id).result == {"review_item_id": item_id}
        assert db.scalar(select(func.count()).select_from(ReviewQueueItem)) == 1


def test_repeated_crashes_exhaust_attempts(companies):
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
        now = tasks.utcnow()
        for attempt in range(3):
            assert tasks.claim(db, now=now)
            now += timedelta(seconds=61)
            assert tasks.recover_expired(db, now=now) == 1
            now += timedelta(seconds=10)
        assert tasks.claim(db, now=now) is None
        task = db.get(InternalTask, task_id, populate_existing=True)
        assert task.status == "failed"
        assert task.attempts == 3
        assert task.error_code == "lease_expired"


def test_conflicting_sync_input_preserves_existing_result(companies):
    from app.services.commercial_pipeline import triage_and_queue
    with TestingSessionLocal() as db:
        original = triage_and_queue(db, trigger(), 1, "synthetic")
        item_id = original.id
        changed = trigger().model_copy(update={"message": "Different synthetic request"})
        task_id = tasks.enqueue(db, changed, 1).id
    assert tasks.run_once(TestingSessionLocal, "synthetic")
    with TestingSessionLocal() as db:
        assert db.get(ReviewQueueItem, item_id).message == trigger().message
        assert db.scalar(select(func.count()).select_from(ReviewQueueItem)) == 1
        task = db.get(InternalTask, task_id)
        assert task.status == "queued"
        assert task.error_code == "processing_failed"
        assert task.result is None


# -- WP-067: manual retry and retention --


def test_manual_retry_resets_failed_task(companies):
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
        now = tasks.utcnow()
        for _ in range(3):
            claimed = tasks.claim(db, now=now)
            now += timedelta(seconds=61)
            tasks.recover_expired(db, now=now)
            now += timedelta(seconds=10)
        task = db.get(InternalTask, task_id, populate_existing=True)
        assert task.status == "failed"
        assert task.attempts == 3
        retried = tasks.manual_retry(db, task_id, 1)
        assert retried is not None
        assert retried.status == "queued"
        assert retried.lease_until is None
        assert retried.claim_token is None
        assert retried.error_code is None
        assert retried.result is None
        assert retried.attempts == 3  # preserved for worker limit


def test_manual_retry_rejects_non_failed(companies):
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
        with pytest.raises(ValueError, match="Only failed"):
            tasks.manual_retry(db, task_id, 1)


def test_manual_retry_returns_none_for_missing_task(companies):
    with TestingSessionLocal() as db:
        assert tasks.manual_retry(db, 999, 1) is None


def test_manual_retry_is_tenant_isolated(companies):
    with TestingSessionLocal() as db:
        task_id = tasks.enqueue(db, trigger(), 1).id
        task = db.get(InternalTask, task_id)
        task.status = "failed"
        db.commit()
        assert tasks.manual_retry(db, task_id, 2) is None


def test_api_manual_retry(companies, client, operator_a_headers, operator_b_headers):
    payload = trigger().model_dump()
    resp = client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
    task_id = resp.json()["id"]
    with TestingSessionLocal() as db:
        task = db.get(InternalTask, task_id)
        task.status = "failed"
        task.error_code = "processing_failed"
        db.commit()
    assert client.post(f"/internal-tasks/{task_id}/retry", headers=operator_a_headers).json()["status"] == "queued"
    assert client.post(f"/internal-tasks/{task_id}/retry", headers=operator_a_headers).status_code == 409
    assert client.post("/internal-tasks/999/retry", headers=operator_a_headers).status_code == 404
    assert client.post(f"/internal-tasks/{task_id}/retry", headers=operator_b_headers).status_code == 404


def test_purge_old_tasks_removes_only_terminal(companies):
    with TestingSessionLocal() as db:
        old = tasks.utcnow() - timedelta(days=60)
        tasks.enqueue(db, trigger(event="old-s"), 1)
        t1 = db.get(InternalTask, 1)
        t1.status = "succeeded"
        t1.created_at = old
        tasks.enqueue(db, trigger(event="old-f"), 1)
        t2 = db.get(InternalTask, 2)
        t2.status = "failed"
        t2.created_at = old
        tasks.enqueue(db, trigger(event="old-q"), 1)
        t3 = db.get(InternalTask, 3)
        t3.status = "queued"
        t3.created_at = old
        tasks.enqueue(db, trigger(event="new-s"), 1)
        t4 = db.get(InternalTask, 4)
        t4.status = "succeeded"
        db.commit()
    with TestingSessionLocal() as db:
        deleted = tasks.purge_old_tasks(db, 1, older_than_days=30)
        assert deleted == 2
        remaining = db.scalars(select(InternalTask).where(InternalTask.company_id == 1)).all()
        assert len(remaining) == 2
        ids = {r.id for r in remaining}
        assert 3 in ids  # queued preserved
        assert 4 in ids  # recent succeeded preserved


def test_purge_old_tasks_tenant_isolation(companies):
    with TestingSessionLocal() as db:
        old = tasks.utcnow() - timedelta(days=60)
        tasks.enqueue(db, trigger(event="a-old"), 1)
        db.get(InternalTask, 1).status = "failed"
        db.get(InternalTask, 1).created_at = old
        tasks.enqueue(db, trigger(event="b-old"), 2)
        db.get(InternalTask, 2).status = "failed"
        db.get(InternalTask, 2).created_at = old
        db.commit()
    with TestingSessionLocal() as db:
        deleted = tasks.purge_old_tasks(db, 1, older_than_days=30)
        assert deleted == 1
        assert db.scalar(select(func.count()).select_from(InternalTask)) == 1


def test_api_retention_endpoint(companies, client, operator_a_headers):
    assert client.post("/internal-tasks/retention", headers=operator_a_headers).json()["deleted"] == 0
    assert client.post("/internal-tasks/retention").status_code == 401
