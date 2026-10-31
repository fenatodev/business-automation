"""WP-172 — Bulk retry for internal tasks.

Tests that bulk retry endpoint is tenant-isolated, returns correct counts,
and properly skips tasks that cannot be retried.
"""
from datetime import datetime, timezone

import pytest

from app.models import Company, InternalTask
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


@pytest.fixture
def company_b():
    with TestingSessionLocal() as db:
        db.add(Company(id=2, name="Synthetic B", slug="synthetic-b"))
        db.commit()


@pytest.fixture
def failed_tasks_a(company_a):
    """Create failed internal tasks in company A."""
    now = datetime.now(timezone.utc)
    with TestingSessionLocal() as db:
        db.add(InternalTask(
            company_id=1, event_id="task-a1", status="failed",
            attempts=3, error_code="TIMEOUT", payload={"action": "test"},
            available_at=now,
        ))
        db.add(InternalTask(
            company_id=1, event_id="task-a2", status="failed",
            attempts=2, error_code="CONNECTION_ERROR", payload={"action": "test"},
            available_at=now,
        ))
        db.commit()


@pytest.fixture
def tasks_b(company_b):
    """Create failed tasks in company B."""
    now = datetime.now(timezone.utc)
    with TestingSessionLocal() as db:
        db.add(InternalTask(
            company_id=2, event_id="task-b1", status="failed",
            attempts=1, error_code="TIMEOUT", payload={"action": "test"},
            available_at=now,
        ))
        db.commit()


class TestBulkRetry:
    """Test POST /internal-tasks/bulk-retry."""

    def test_bulk_retry_failed_tasks(self, client, operator_a_headers, failed_tasks_a):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1, 2],
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["retried"] == 2
        assert resp.json()["skipped"] == []

    def test_bulk_retry_returns_ids(self, client, operator_a_headers, failed_tasks_a):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1, 2],
        }, headers=operator_a_headers)
        assert sorted(resp.json()["retried_ids"]) == [1, 2]

    def test_bulk_retry_resets_status(self, client, operator_a_headers, failed_tasks_a):
        client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1],
        }, headers=operator_a_headers)
        resp = client.get("/internal-tasks/1", headers=operator_a_headers)
        assert resp.json()["status"] == "queued"

    def test_bulk_retry_skips_non_failed(self, client, operator_a_headers, failed_tasks_a):
        # Retry once to queue
        client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1],
        }, headers=operator_a_headers)
        # Retry again should skip (not failed)
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1, 2],
        }, headers=operator_a_headers)
        assert resp.json()["retried"] == 1
        assert 1 in resp.json()["skipped"]

    def test_bulk_retry_tenant_isolation(self, client, operator_a_headers, tasks_b):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1],
        }, headers=operator_a_headers)
        assert resp.json()["retried"] == 0
        assert 1 in resp.json()["skipped"]

    def test_bulk_retry_requires_auth(self, client):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1],
        })
        assert resp.status_code in (401, 403)

    def test_bulk_retry_single_item(self, client, operator_a_headers, failed_tasks_a):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1],
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["retried"] == 1

    def test_bulk_retry_empty_rejected(self, client, operator_a_headers):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [],
        }, headers=operator_a_headers)
        assert resp.status_code == 422

    def test_bulk_retry_skips_nonexistent(self, client, operator_a_headers, failed_tasks_a):
        resp = client.post("/internal-tasks/bulk-retry", json={
            "task_ids": [1, 99999],
        }, headers=operator_a_headers)
        assert resp.json()["retried"] == 1
        assert 99999 in resp.json()["skipped"]
