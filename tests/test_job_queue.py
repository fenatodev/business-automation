"""WP-532 — Job queue in-memory tests."""
import time

from app.services.job_queue import JobQueue, JobStatus


def _fresh_queue():
    return JobQueue()


# --- Job creation ---


def test_create_job():
    """Create a job returns pending status."""
    q = _fresh_queue()
    job = q.create_job(task_type="test", company_id=1)
    assert job.status == JobStatus.PENDING
    assert job.task_type == "test"
    assert job.company_id == 1
    assert job.job_id is not None


def test_create_job_with_payload():
    """Create a job with payload."""
    q = _fresh_queue()
    job = q.create_job(task_type="test", payload={"key": "value"})
    assert job.payload == {"key": "value"}


def test_create_job_generates_uuid():
    """Each job gets a unique ID."""
    q = _fresh_queue()
    j1 = q.create_job(task_type="a")
    j2 = q.create_job(task_type="b")
    assert j1.job_id != j2.job_id


# --- Job retrieval ---


def test_get_job():
    """Get job by ID."""
    q = _fresh_queue()
    job = q.create_job(task_type="test")
    found = q.get_job(job.job_id)
    assert found is job


def test_get_job_not_found():
    """Get non-existent job returns None."""
    q = _fresh_queue()
    assert q.get_job("nonexistent") is None


# --- Job listing ---


def test_list_jobs():
    """List jobs returns all jobs."""
    q = _fresh_queue()
    q.create_job(task_type="a", company_id=1)
    q.create_job(task_type="b", company_id=1)
    jobs = q.list_jobs(company_id=1)
    assert len(jobs) == 2


def test_list_jobs_filter_by_company():
    """List jobs filters by company_id."""
    q = _fresh_queue()
    q.create_job(task_type="a", company_id=1)
    q.create_job(task_type="b", company_id=2)
    jobs = q.list_jobs(company_id=1)
    assert len(jobs) == 1
    assert jobs[0].company_id == 1


def test_list_jobs_filter_by_status():
    """List jobs filters by status."""
    q = _fresh_queue()
    q.create_job(task_type="a")
    q.create_job(task_type="b")
    jobs = q.list_jobs(status=JobStatus.PENDING)
    assert len(jobs) == 2


def test_list_jobs_limit():
    """List jobs respects limit."""
    q = _fresh_queue()
    for i in range(5):
        q.create_job(task_type=f"job-{i}")
    jobs = q.list_jobs(limit=2)
    assert len(jobs) == 2


def test_list_jobs_sorted_desc():
    """List jobs sorted by created_at descending."""
    q = _fresh_queue()
    j1 = q.create_job(task_type="first")
    time.sleep(0.01)
    j2 = q.create_job(task_type="second")
    jobs = q.list_jobs()
    assert jobs[0].job_id == j2.job_id
    assert jobs[1].job_id == j1.job_id


# --- Job execution ---


def test_execute_job_sync_success():
    """Execute job synchronously succeeds."""
    q = _fresh_queue()
    job = q.create_job(task_type="test", payload={"x": 1})
    q.execute_job(job.job_id, lambda x: x * 2, _async=False)
    assert job.status == JobStatus.COMPLETED
    assert job.result == 2


def test_execute_job_sync_failure():
    """Execute job synchronously captures error."""
    q = _fresh_queue()
    job = q.create_job(task_type="test")
    def failing_func():
        raise ValueError("test error")
    q.execute_job(job.job_id, failing_func, _async=False)
    assert job.status == JobStatus.FAILED
    assert "test error" in job.error


def test_execute_job_sets_timestamps():
    """Execute job sets started_at and completed_at."""
    q = _fresh_queue()
    job = q.create_job(task_type="test")
    q.execute_job(job.job_id, lambda: "ok", _async=False)
    assert job.started_at is not None
    assert job.completed_at is not None


def test_execute_job_not_found():
    """Execute non-existent job raises KeyError."""
    q = _fresh_queue()
    try:
        q.execute_job("nonexistent", lambda: None, _async=False)
        assert False, "Expected KeyError"
    except KeyError:
        pass


# --- Cleanup ---


def test_cleanup_completed():
    """Cleanup removes old completed jobs."""
    q = _fresh_queue()
    job = q.create_job(task_type="test")
    q.execute_job(job.job_id, lambda: "ok", _async=False)
    # Set completed_at to old time
    from datetime import datetime, timezone, timedelta
    job.completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
    removed = q.cleanup_completed(older_than_seconds=3600)
    assert removed == 1
    assert q.get_job(job.job_id) is None


def test_cleanup_keeps_recent():
    """Cleanup keeps recent jobs."""
    q = _fresh_queue()
    job = q.create_job(task_type="test")
    q.execute_job(job.job_id, lambda: "ok", _async=False)
    removed = q.cleanup_completed(older_than_seconds=3600)
    assert removed == 0
    assert q.get_job(job.job_id) is not None


# --- API endpoints ---


def test_create_job_endpoint(client, operator_a_headers):
    """POST /operator/jobs creates a job."""
    res = client.post(
        "/operator/jobs",
        headers=operator_a_headers,
        json={"task_type": "test", "payload": {"key": "value"}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["task_type"] == "test"
    assert data["status"] == "pending"


def test_get_job_endpoint(client, operator_a_headers):
    """GET /operator/jobs/{id} returns job status."""
    create_res = client.post(
        "/operator/jobs",
        headers=operator_a_headers,
        json={"task_type": "test"},
    )
    job_id = create_res.json()["job_id"]

    res = client.get(
        f"/operator/jobs/{job_id}",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["job_id"] == job_id


def test_get_job_not_found(client, operator_a_headers):
    """GET /operator/jobs/{id} returns 404 for unknown job."""
    res = client.get(
        "/operator/jobs/nonexistent",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_list_jobs_endpoint(client, operator_a_headers):
    """GET /operator/jobs lists jobs."""
    client.post(
        "/operator/jobs",
        headers=operator_a_headers,
        json={"task_type": "test"},
    )
    res = client.get(
        "/operator/jobs",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert len(data["jobs"]) >= 1


def test_job_requires_auth(client):
    """Job endpoints require authentication."""
    res = client.post("/operator/jobs", json={"task_type": "test"})
    assert res.status_code in (401, 403)


def test_job_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot access Operator B's jobs."""
    create_res = client.post(
        "/operator/jobs",
        headers=operator_b_headers,
        json={"task_type": "secret"},
    )
    job_id = create_res.json()["job_id"]

    res = client.get(
        f"/operator/jobs/{job_id}",
        headers=operator_a_headers,
    )
    assert res.status_code == 403
