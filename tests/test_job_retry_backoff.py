"""WP-540 — Job retry with exponential backoff tests."""
from datetime import datetime, timedelta, timezone

from app.services.job_queue import Job, JobQueue, JobStatus


def _new_queue():
    return JobQueue()


# --- Job retry fields ---


def test_job_has_retry_fields():
    """Job has max_retries, retry_count, next_retry_at, backoff_multiplier."""
    job = Job()
    assert job.max_retries == 3
    assert job.retry_count == 0
    assert job.next_retry_at is None
    assert job.backoff_multiplier == 2.0


def test_job_custom_retry_config():
    """Job accepts custom retry config."""
    job = Job(max_retries=5, backoff_multiplier=3.0)
    assert job.max_retries == 5
    assert job.retry_count == 0
    assert job.backoff_multiplier == 3.0


# --- Backoff calculation ---


def test_calculate_backoff_first_retry():
    """First retry backoff is multiplier^(1-1) = 1.0."""
    q = _new_queue()
    assert q._calculate_backoff(1, 2.0) == 1.0


def test_calculate_backoff_second_retry():
    """Second retry backoff is multiplier^(2-1) = 2.0."""
    q = _new_queue()
    assert q._calculate_backoff(2, 2.0) == 2.0


def test_calculate_backoff_third_retry():
    """Third retry backoff is multiplier^(3-1) = 4.0."""
    q = _new_queue()
    assert q._calculate_backoff(3, 2.0) == 4.0


def test_calculate_backoff_custom_multiplier():
    """Custom multiplier works correctly."""
    q = _new_queue()
    assert q._calculate_backoff(1, 3.0) == 1.0
    assert q._calculate_backoff(2, 3.0) == 3.0
    assert q._calculate_backoff(3, 3.0) == 9.0


# --- Automatic retry on failure ---


def test_job_auto_retry_on_failure():
    """Failed job is scheduled for retry with backoff."""
    q = _new_queue()
    job = q.create_job("test", max_retries=3, backoff_multiplier=2.0)

    def failing_func():
        raise ValueError("test error")

    q.execute_job(job.job_id, failing_func, _async=False)

    assert job.status == JobStatus.PENDING
    assert job.retry_count == 1
    assert job.next_retry_at is not None
    assert job.error == "test error"


def test_job_exhausts_retries():
    """Job becomes FAILED after exhausting all retries."""
    q = _new_queue()
    job = q.create_job("test", max_retries=2, backoff_multiplier=1.0)

    def failing_func():
        raise ValueError("test error")

    # First attempt (retry_count=0 → 1)
    q.execute_job(job.job_id, failing_func, _async=False)
    assert job.status == JobStatus.PENDING
    assert job.retry_count == 1

    # Second attempt (retry_count=1 → 2)
    q.execute_job(job.job_id, failing_func, _async=False)
    assert job.status == JobStatus.PENDING
    assert job.retry_count == 2

    # Third attempt (retry_count=2 == max_retries → FAILED)
    q.execute_job(job.job_id, failing_func, _async=False)
    assert job.status == JobStatus.FAILED
    assert job.retry_count == 2
    assert job.completed_at is not None


def test_job_no_retry_when_max_retries_zero():
    """Job with max_retries=0 fails immediately without retry."""
    q = _new_queue()
    job = q.create_job("test", max_retries=0, backoff_multiplier=1.0)

    def failing_func():
        raise ValueError("test error")

    q.execute_job(job.job_id, failing_func, _async=False)
    assert job.status == JobStatus.FAILED
    assert job.retry_count == 0
    assert job.next_retry_at is None


# --- Manual retry endpoint ---


def test_retry_job_resets_failed_job():
    """retry_job resets a FAILED job to PENDING."""
    q = _new_queue()
    job = q.create_job("test", max_retries=2, backoff_multiplier=1.0)

    def failing_func():
        raise ValueError("test error")

    # Exhaust retries: first run → retry_count=1 (PENDING), second → retry_count=2 (PENDING), third → FAILED
    for _ in range(3):
        q.execute_job(job.job_id, failing_func, _async=False)

    assert job.status == JobStatus.FAILED

    # Manual retry
    q.retry_job(job.job_id)
    assert job.status == JobStatus.PENDING
    assert job.error is None
    assert job.result is None
    assert job.started_at is None
    assert job.completed_at is None
    assert job.next_retry_at is None


def test_retry_job_not_found():
    """retry_job raises KeyError for unknown job."""
    q = _new_queue()
    try:
        q.retry_job("nonexistent")
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_retry_job_wrong_status():
    """retry_job raises ValueError for non-FAILED jobs."""
    q = _new_queue()
    job = q.create_job("test")
    assert job.status == JobStatus.PENDING

    try:
        q.retry_job(job.job_id)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_retry_job_completed_status():
    """retry_job raises ValueError for COMPLETED jobs."""
    q = _new_queue()
    job = q.create_job("test")

    def success_func():
        return "ok"

    q.execute_job(job.job_id, success_func, _async=False)
    assert job.status == JobStatus.COMPLETED

    try:
        q.retry_job(job.job_id)
        assert False, "Expected ValueError"
    except ValueError:
        pass


# --- get_pending_retries ---


def test_get_pending_retries_empty():
    """get_pending_retries returns empty list when no retries."""
    q = _new_queue()
    assert q.get_pending_retries() == []


def test_get_pending_retries_returns_ready_jobs():
    """get_pending_retries returns jobs with next_retry_at <= now."""
    q = _new_queue()
    job = q.create_job("test", max_retries=3, backoff_multiplier=1.0)
    job.status = JobStatus.PENDING
    job.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    retries = q.get_pending_retries()
    assert job in retries


def test_get_pending_retries_skips_future_jobs():
    """get_pending_retries skips jobs with next_retry_at in the future."""
    q = _new_queue()
    job = q.create_job("test", max_retries=3, backoff_multiplier=1.0)
    job.status = JobStatus.PENDING
    job.next_retry_at = datetime.now(timezone.utc) + timedelta(hours=1)

    retries = q.get_pending_retries()
    assert job not in retries


# --- create_job with retry config ---


def test_create_job_with_retry_config():
    """create_job passes retry config to Job."""
    q = _new_queue()
    job = q.create_job("test", max_retries=5, backoff_multiplier=3.0)
    assert job.max_retries == 5
    assert job.backoff_multiplier == 3.0
    assert job.retry_count == 0


# --- Endpoint tests ---


def test_retry_job_endpoint_not_found(client, operator_a_headers):
    """POST /jobs/{id}/retry returns 404 for unknown job."""
    resp = client.post(
        "/operator/jobs/nonexistent/retry",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_retry_job_endpoint_wrong_status(client, operator_a_headers):
    """POST /jobs/{id}/retry returns 400 for non-FAILED job."""
    resp = client.post(
        "/operator/jobs",
        json={"task_type": "test"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    resp = client.post(
        f"/operator/jobs/{job_id}/retry",
        headers=operator_a_headers,
    )
    assert resp.status_code == 400


def test_retry_job_endpoint_success(client, operator_a_headers):
    """POST /jobs/{id}/retry resets a FAILED job."""
    from app.services.job_queue import job_queue

    # Create a job and fail it
    job = job_queue.create_job("test", max_retries=0, backoff_multiplier=1.0)

    def failing_func():
        raise ValueError("test error")

    job_queue.execute_job(job.job_id, failing_func, _async=False)
    assert job.status == JobStatus.FAILED

    resp = client.post(
        f"/operator/jobs/{job.job_id}/retry",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["error"] is None


def test_retry_job_endpoint_tenant_isolation(client, operator_a_headers):
    """POST /jobs/{id}/retry returns 403 for other company jobs."""
    from app.services.job_queue import job_queue

    job = job_queue.create_job("test", company_id=99999, max_retries=0)

    def failing_func():
        raise ValueError("test error")

    job_queue.execute_job(job.job_id, failing_func, _async=False)

    resp = client.post(
        f"/operator/jobs/{job.job_id}/retry",
        headers=operator_a_headers,
    )
    assert resp.status_code == 403


def test_retry_job_endpoint_requires_auth(client):
    """POST /jobs/{id}/retry returns 401 without auth."""
    resp = client.post("/operator/jobs/nonexistent/retry")
    assert resp.status_code in (401, 403)


def test_create_job_with_retry_config_endpoint(client, operator_a_headers):
    """POST /jobs accepts max_retries and backoff_multiplier."""
    resp = client.post(
        "/operator/jobs",
        json={
            "task_type": "test",
            "max_retries": 5,
            "backoff_multiplier": 3.0,
        },
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_retries"] == 5
    assert data["retry_count"] == 0


def test_job_status_response_includes_retry_fields(client, operator_a_headers):
    """GET /jobs/{id} includes retry fields in response."""
    resp = client.post(
        "/operator/jobs",
        json={"task_type": "test", "max_retries": 4},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    resp = client.get(
        f"/operator/jobs/{job_id}",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "retry_count" in data
    assert "max_retries" in data
    assert "next_retry_at" in data
    assert data["max_retries"] == 4
    assert data["retry_count"] == 0
