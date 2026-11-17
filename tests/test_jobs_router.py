"""Jobs router tests — dedicated coverage for all 5 endpoints.

Covers GET /jobs/, GET /jobs/pending-retries, POST /jobs/{id}/retry,
POST /jobs/cleanup, and GET /jobs/{id}/error with proper isolation.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.services.job_queue import job_queue, JobStatus


@pytest.fixture(autouse=True)
def _clear_job_queue():
    """Clear the in-memory job queue before and after each test."""
    job_queue._jobs.clear()
    yield
    job_queue._jobs.clear()


def _create_job(task_type="generic", company_id=None, payload=None, max_retries=3):
    """Helper to create a job and return its dict."""
    job = job_queue.create_job(
        task_type=task_type,
        company_id=company_id,
        payload=payload or {},
        max_retries=max_retries,
    )
    return job


def test_list_jobs_empty(client):
    """Returns empty list when no jobs exist."""
    res = client.get("/jobs/")
    assert res.status_code == 200
    assert res.json() == []


def test_list_jobs_returns_created_jobs(client):
    """Returns jobs that were created."""
    j1 = _create_job(task_type="agent-reply", company_id=1)
    j2 = _create_job(task_type="summary", company_id=1)

    res = client.get("/jobs/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    job_ids = [j["job_id"] for j in data]
    assert j1.job_id in job_ids
    assert j2.job_id in job_ids


def test_list_jobs_filter_by_company_id(client):
    """Filters jobs by company_id."""
    _create_job(task_type="a", company_id=1)
    _create_job(task_type="b", company_id=2)
    _create_job(task_type="c", company_id=1)

    res = client.get("/jobs/?company_id=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    for j in data:
        assert j["company_id"] == 1


def test_list_jobs_filter_by_status(client):
    """Filters jobs by status."""
    j1 = _create_job(task_type="a")
    j2 = _create_job(task_type="b")
    # Manually set one to completed
    j2.status = JobStatus.COMPLETED

    res = client.get("/jobs/?status=pending")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["job_id"] == j1.job_id


def test_list_jobs_limit(client):
    """Respects the limit parameter."""
    for i in range(5):
        _create_job(task_type=f"job-{i}")

    res = client.get("/jobs/?limit=2")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_jobs_sorted_by_created_at_desc(client):
    """Jobs are sorted by created_at descending (newest first)."""
    j1 = _create_job(task_type="first")
    j2 = _create_job(task_type="second")
    j3 = _create_job(task_type="third")

    res = client.get("/jobs/")
    data = res.json()
    assert len(data) == 3
    # Newest first
    assert data[0]["job_id"] == j3.job_id
    assert data[1]["job_id"] == j2.job_id
    assert data[2]["job_id"] == j1.job_id


def test_pending_retries_empty(client):
    """Returns empty list when no pending retries."""
    _create_job(task_type="a")

    res = client.get("/jobs/pending-retries")
    assert res.status_code == 200
    assert res.json() == []


def test_pending_retries_returns_scheduled_jobs(client):
    """Returns jobs with next_retry_at in the past."""
    j = _create_job(task_type="a", max_retries=3)
    # Simulate a job scheduled for retry in the past
    j.status = JobStatus.PENDING
    j.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    j.retry_count = 1

    res = client.get("/jobs/pending-retries")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["job_id"] == j.job_id


def test_pending_retries_excludes_future_retry(client):
    """Excludes jobs with next_retry_at in the future."""
    j = _create_job(task_type="a", max_retries=3)
    j.status = JobStatus.PENDING
    j.next_retry_at = datetime.now(timezone.utc) + timedelta(hours=1)
    j.retry_count = 1

    res = client.get("/jobs/pending-retries")
    assert res.status_code == 200
    assert res.json() == []


def test_retry_job_success(client):
    """Successfully retries a failed job."""
    j = _create_job(task_type="a", max_retries=0)
    j.status = JobStatus.FAILED
    j.error = "Test error"

    res = client.post(f"/jobs/{j.job_id}/retry")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert data["error"] is None


def test_retry_job_not_found(client):
    """Returns 404 when retrying a nonexistent job."""
    res = client.post("/jobs/nonexistent-id/retry")
    assert res.status_code == 404


def test_retry_job_wrong_status(client):
    """Returns 400 when retrying a non-failed job."""
    j = _create_job(task_type="a")
    # Job is PENDING, not FAILED

    res = client.post(f"/jobs/{j.job_id}/retry")
    assert res.status_code == 400


def test_cleanup_jobs_removes_old_completed(client):
    """Removes completed jobs older than threshold."""
    j1 = _create_job(task_type="a")
    j1.status = JobStatus.COMPLETED
    j1.completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)

    j2 = _create_job(task_type="b")
    j2.status = JobStatus.COMPLETED
    j2.completed_at = datetime.now(timezone.utc) - timedelta(seconds=1800)

    # Cleanup jobs older than 3600 seconds
    res = client.post("/jobs/cleanup?older_than_seconds=3600")
    assert res.status_code == 200
    assert res.json() == 1  # Only j1 removed

    # Verify j2 still exists
    assert job_queue.get_job(j2.job_id) is not None
    assert job_queue.get_job(j1.job_id) is None


def test_cleanup_jobs_removes_old_failed(client):
    """Removes failed jobs older than threshold."""
    j = _create_job(task_type="a")
    j.status = JobStatus.FAILED
    j.completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)

    res = client.post("/jobs/cleanup?older_than_seconds=3600")
    assert res.status_code == 200
    assert res.json() == 1


def test_cleanup_jobs_keeps_recent_jobs(client):
    """Does not remove recently completed jobs."""
    j = _create_job(task_type="a")
    j.status = JobStatus.COMPLETED
    j.completed_at = datetime.now(timezone.utc) - timedelta(seconds=60)

    res = client.post("/jobs/cleanup?older_than_seconds=3600")
    assert res.status_code == 200
    assert res.json() == 0
    assert job_queue.get_job(j.job_id) is not None


def test_cleanup_jobs_keeps_pending_jobs(client):
    """Does not remove pending or running jobs."""
    j = _create_job(task_type="a")
    j.status = JobStatus.PENDING

    res = client.post("/jobs/cleanup?older_than_seconds=3600")
    assert res.status_code == 200
    assert res.json() == 0


def test_cleanup_default_threshold(client):
    """Uses default threshold of 3600 seconds."""
    j = _create_job(task_type="a")
    j.status = JobStatus.COMPLETED
    j.completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)

    res = client.post("/jobs/cleanup")
    assert res.status_code == 200
    assert res.json() == 1


def test_get_job_error_returns_error_message(client):
    """Returns the error message for a failed job."""
    j = _create_job(task_type="a", max_retries=0)
    j.status = JobStatus.FAILED
    j.error = "Connection timeout"

    res = client.get(f"/jobs/{j.job_id}/error")
    assert res.status_code == 200
    assert res.json() == "Connection timeout"


def test_get_job_error_not_found(client):
    """Returns 404 for nonexistent job."""
    res = client.get("/jobs/nonexistent-id/error")
    assert res.status_code == 404


def test_get_job_error_job_not_failed(client):
    """Returns 400 when job is not in FAILED status."""
    j = _create_job(task_type="a")
    # Job is PENDING

    res = client.get(f"/jobs/{j.job_id}/error")
    assert res.status_code == 400


def test_get_job_error_no_error_recorded(client):
    """Returns 404 when failed job has no error message."""
    j = _create_job(task_type="a", max_retries=0)
    j.status = JobStatus.FAILED
    j.error = None

    res = client.get(f"/jobs/{j.job_id}/error")
    assert res.status_code == 404


def test_list_jobs_with_combined_filters(client):
    """Combines company_id and status filters."""
    _create_job(task_type="a", company_id=1)
    _create_job(task_type="b", company_id=1)
    j3 = _create_job(task_type="c", company_id=1)
    j3.status = JobStatus.COMPLETED
    _create_job(task_type="d", company_id=2)

    res = client.get("/jobs/?company_id=1&status=pending")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_retry_job_resets_state(client):
    """Retry resets all state fields for re-execution."""
    j = _create_job(task_type="a", max_retries=0)
    j.status = JobStatus.FAILED
    j.error = "Old error"
    j.result = "old result"
    j.started_at = datetime.now(timezone.utc)
    j.completed_at = datetime.now(timezone.utc)
    j.next_retry_at = datetime.now(timezone.utc)

    res = client.post(f"/jobs/{j.job_id}/retry")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert data["error"] is None
    assert data["result"] is None
    assert data["started_at"] is None
    assert data["completed_at"] is None
    assert data["next_retry_at"] is None
