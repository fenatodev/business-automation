"""Scheduler router endpoints: CRUD, toggle, run-now, start/stop, auth.

Cobre os 7 endpoints do scheduler.py que tinham apenas 3 testes:
criação, listagem, cancelamento, toggle, run-now, start e stop.
"""
from app.services.scheduler import scheduler


def _clear_scheduler():
    """Remove all scheduled jobs and stop scheduler for clean test state."""
    for job in list(scheduler.list()):
        scheduler.remove(job.scheduled_id)
    scheduler.stop()


def test_create_scheduled_job(client, operator_a_headers):
    """POST /scheduler/ creates a new scheduled job."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={
            "name": "Daily cleanup",
            "interval_seconds": 86400,
            "task_type": "scheduled",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Daily cleanup"
    assert data["interval_seconds"] == 86400
    assert data["task_type"] == "scheduled"
    assert data["enabled"] is True
    assert "scheduled_id" in data


def test_create_scheduled_job_with_followup_task_type(client, operator_a_headers):
    """POST /scheduler/ creates a followup job with task_type='followup'."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={
            "name": "Followup check",
            "interval_seconds": 3600,
            "task_type": "followup",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["task_type"] == "followup"


def test_create_scheduled_job_with_payload(client, operator_a_headers):
    """POST /scheduler/ accepts optional payload dict."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={
            "name": "Custom job",
            "interval_seconds": 60,
            "payload": {"key": "value"},
        },
    )
    assert res.status_code == 201
    assert res.json()["name"] == "Custom job"


def test_create_scheduled_job_invalid_interval(client, operator_a_headers):
    """POST /scheduler/ rejects interval_seconds < 1 (ValueError propagates as 500)."""
    _clear_scheduler()
    import pytest as _pytest
    with _pytest.raises(ValueError, match="interval_seconds must be >= 1"):
        client.post(
            "/scheduler/",
            headers=operator_a_headers,
            json={
                "name": "Bad interval",
                "interval_seconds": 0,
            },
        )


def test_create_scheduled_job_missing_name(client, operator_a_headers):
    """POST /scheduler/ rejects missing name field."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"interval_seconds": 60},
    )
    assert res.status_code == 422


def test_create_scheduled_job_requires_auth(client):
    """POST /scheduler/ without auth returns 401."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/",
        json={"name": "No auth", "interval_seconds": 60},
    )
    assert res.status_code in (401, 403)


def test_list_scheduled_jobs_empty(client, operator_a_headers):
    """GET /scheduler/ returns empty list when no jobs exist."""
    _clear_scheduler()
    res = client.get("/scheduler/", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_scheduled_jobs_returns_created(client, operator_a_headers):
    """GET /scheduler/ returns created jobs."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "Listed job", "interval_seconds": 300},
    )
    assert create_res.status_code == 201

    res = client.get("/scheduler/", headers=operator_a_headers)
    assert res.status_code == 200
    jobs = res.json()
    assert len(jobs) >= 1
    assert any(j["name"] == "Listed job" for j in jobs)


def test_list_scheduled_jobs_requires_auth(client):
    """GET /scheduler/ without auth returns 401."""
    res = client.get("/scheduler/")
    assert res.status_code in (401, 403)


def test_cancel_scheduled_job(client, operator_a_headers):
    """PATCH /scheduler/{id}/cancel removes a scheduled job."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "To cancel", "interval_seconds": 120},
    )
    job_id = create_res.json()["scheduled_id"]

    res = client.patch(
        f"/scheduler/{job_id}/cancel",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json() is True

    # Verify removed
    list_res = client.get("/scheduler/", headers=operator_a_headers)
    assert all(j["scheduled_id"] != job_id for j in list_res.json())


def test_cancel_nonexistent_job(client, operator_a_headers):
    """PATCH /scheduler/{id}/cancel for nonexistent job returns 404."""
    _clear_scheduler()
    res = client.patch(
        "/scheduler/nonexistent-id/cancel",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_cancel_scheduled_job_requires_auth(client):
    """PATCH /scheduler/{id}/cancel without auth returns 401."""
    res = client.patch("/scheduler/some-id/cancel")
    assert res.status_code in (401, 403)


def test_toggle_scheduled_job_disable(client, operator_a_headers):
    """POST /scheduler/{id}/toggle with enabled=false disables a job."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "Toggle job", "interval_seconds": 60},
    )
    job_id = create_res.json()["scheduled_id"]

    res = client.post(
        f"/scheduler/{job_id}/toggle?enabled=false",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["enabled"] is False


def test_toggle_scheduled_job_enable(client, operator_a_headers):
    """POST /scheduler/{id}/toggle with enabled=true enables a job."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "Toggle job 2", "interval_seconds": 60},
    )
    job_id = create_res.json()["scheduled_id"]

    # Disable first
    client.post(
        f"/scheduler/{job_id}/toggle?enabled=false",
        headers=operator_a_headers,
    )

    # Re-enable
    res = client.post(
        f"/scheduler/{job_id}/toggle?enabled=true",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["enabled"] is True


def test_toggle_nonexistent_job(client, operator_a_headers):
    """POST /scheduler/{id}/toggle for nonexistent job returns 404."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/nonexistent-id/toggle?enabled=true",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_toggle_scheduled_job_requires_auth(client):
    """POST /scheduler/{id}/toggle without auth returns 401."""
    res = client.post("/scheduler/some-id/toggle?enabled=true")
    assert res.status_code in (401, 403)


def test_run_now_scheduled_job(client, operator_a_headers):
    """POST /scheduler/{id}/run-now triggers a job immediately."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "Run now job", "interval_seconds": 60},
    )
    job_id = create_res.json()["scheduled_id"]

    res = client.post(
        f"/scheduler/{job_id}/run-now",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data is not None
    assert "job_id" in data


def test_run_now_nonexistent_job(client, operator_a_headers):
    """POST /scheduler/{id}/run-now for nonexistent job returns None."""
    _clear_scheduler()
    res = client.post(
        "/scheduler/nonexistent-id/run-now",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json() is None


def test_run_now_scheduled_job_requires_auth(client):
    """POST /scheduler/{id}/run-now without auth returns 401."""
    res = client.post("/scheduler/some-id/run-now")
    assert res.status_code in (401, 403)


def test_start_scheduler(client, operator_a_headers):
    """POST /scheduler/start starts the scheduler."""
    _clear_scheduler()
    res = client.post("/scheduler/start", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() is True


def test_start_scheduler_already_running(client, operator_a_headers):
    """POST /scheduler/start returns False when already running."""
    _clear_scheduler()
    client.post("/scheduler/start", headers=operator_a_headers)
    res = client.post("/scheduler/start", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() is False
    scheduler.stop()


def test_stop_scheduler(client, operator_a_headers):
    """POST /scheduler/stop stops the scheduler."""
    _clear_scheduler()
    scheduler.start()
    res = client.post("/scheduler/stop", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() is True


def test_stop_scheduler_not_running(client, operator_a_headers):
    """POST /scheduler/stop returns False when not running."""
    _clear_scheduler()
    res = client.post("/scheduler/stop", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() is False


def test_start_scheduler_requires_auth(client):
    """POST /scheduler/start without auth returns 401."""
    res = client.post("/scheduler/start")
    assert res.status_code in (401, 403)


def test_stop_scheduler_requires_auth(client):
    """POST /scheduler/stop without auth returns 401."""
    res = client.post("/scheduler/stop")
    assert res.status_code in (401, 403)


def test_create_multiple_jobs(client, operator_a_headers):
    """Creating multiple jobs persists all in list."""
    _clear_scheduler()
    for i in range(3):
        res = client.post(
            "/scheduler/",
            headers=operator_a_headers,
            json={"name": f"Job {i}", "interval_seconds": 60 * (i + 1)},
        )
        assert res.status_code == 201

    list_res = client.get("/scheduler/", headers=operator_a_headers)
    jobs = list_res.json()
    names = [j["name"] for j in jobs]
    assert "Job 0" in names
    assert "Job 1" in names
    assert "Job 2" in names


def test_cancel_then_list_removes_job(client, operator_a_headers):
    """Canceling a job removes it from the list."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "Remove me", "interval_seconds": 60},
    )
    job_id = create_res.json()["scheduled_id"]

    before = client.get("/scheduler/", headers=operator_a_headers).json()
    assert len(before) >= 1

    client.patch(f"/scheduler/{job_id}/cancel", headers=operator_a_headers)

    after = client.get("/scheduler/", headers=operator_a_headers).json()
    assert len(after) < len(before)


def test_run_now_updates_last_run_at(client, operator_a_headers):
    """POST /scheduler/{id}/run-now updates last_run_at on the job."""
    _clear_scheduler()
    create_res = client.post(
        "/scheduler/",
        headers=operator_a_headers,
        json={"name": "Run now update", "interval_seconds": 60},
    )
    job_id = create_res.json()["scheduled_id"]

    # Before run-now, last_run_at is None
    list_before = client.get("/scheduler/", headers=operator_a_headers).json()
    job_before = [j for j in list_before if j["scheduled_id"] == job_id][0]
    assert job_before["last_run_at"] is None

    # Run now
    client.post(f"/scheduler/{job_id}/run-now", headers=operator_a_headers)

    # After run-now, last_run_at is set
    list_after = client.get("/scheduler/", headers=operator_a_headers).json()
    job_after = [j for j in list_after if j["scheduled_id"] == job_id][0]
    assert job_after["last_run_at"] is not None
