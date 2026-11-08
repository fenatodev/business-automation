"""WP-542 — Scheduled jobs (cron-like) tests."""
import time

from app.services.job_queue import JobQueue
from app.services.scheduler import Scheduler, ScheduledJob


def _new_scheduler():
    q = JobQueue()
    return Scheduler(job_queue=q)


# --- ScheduledJob ---


def test_scheduled_job_defaults():
    """ScheduledJob has correct defaults."""
    sj = ScheduledJob(name="test", interval_seconds=60)
    assert sj.name == "test"
    assert sj.interval_seconds == 60
    assert sj.enabled is True
    assert sj.last_run_at is None
    assert sj.next_run_at is None


# --- Scheduler CRUD ---


def test_add_scheduled_job():
    """Add a scheduled job."""
    s = _new_scheduler()
    sj = s.add("cleanup", interval_seconds=3600, task_type="cleanup")
    assert sj.name == "cleanup"
    assert sj.interval_seconds == 3600
    assert sj.task_type == "cleanup"


def test_add_invalid_interval():
    """Add rejects interval < 1."""
    s = _new_scheduler()
    try:
        s.add("bad", interval_seconds=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_get_scheduled_job():
    """Get a scheduled job by ID."""
    s = _new_scheduler()
    sj = s.add("test", interval_seconds=60)
    retrieved = s.get(sj.scheduled_id)
    assert retrieved is not None
    assert retrieved.name == "test"


def test_get_nonexistent():
    """Get returns None for unknown ID."""
    s = _new_scheduler()
    assert s.get("nonexistent") is None


def test_list_scheduled_jobs():
    """List all scheduled jobs."""
    s = _new_scheduler()
    s.add("a", interval_seconds=60)
    s.add("b", interval_seconds=120)
    jobs = s.list()
    assert len(jobs) == 2


def test_remove_scheduled_job():
    """Remove a scheduled job."""
    s = _new_scheduler()
    sj = s.add("test", interval_seconds=60)
    assert s.remove(sj.scheduled_id) is True
    assert s.get(sj.scheduled_id) is None


def test_remove_nonexistent():
    """Remove returns False for unknown ID."""
    s = _new_scheduler()
    assert s.remove("nonexistent") is False


def test_toggle_scheduled_job():
    """Toggle a scheduled job on/off."""
    s = _new_scheduler()
    sj = s.add("test", interval_seconds=60)
    s.toggle(sj.scheduled_id, False)
    assert s.get(sj.scheduled_id).enabled is False
    s.toggle(sj.scheduled_id, True)
    assert s.get(sj.scheduled_id).enabled is True


# --- run_now ---


def test_run_now():
    """Manually trigger a scheduled job."""
    s = _new_scheduler()
    sj = s.add("test", interval_seconds=3600)
    job = s.run_now(sj.scheduled_id)
    assert job is not None
    assert sj.last_run_at is not None
    assert sj.last_job_id == job.job_id


def test_run_now_nonexistent():
    """run_now returns None for unknown ID."""
    s = _new_scheduler()
    assert s.run_now("nonexistent") is None


# --- Scheduler start/stop ---


def test_scheduler_start_stop():
    """Scheduler starts and stops cleanly."""
    s = _new_scheduler()
    s.start()
    assert s._running is True
    s.stop()
    assert s._running is False


def test_scheduler_runs_scheduled_job():
    """Scheduler executes a job after interval."""
    s = _new_scheduler()
    sj = s.add("quick", interval_seconds=1, task_type="test")
    sj.next_run_at = sj.created_at  # Run immediately
    s.start()
    time.sleep(2)
    s.stop()
    assert sj.last_run_at is not None


def test_scheduler_skips_disabled():
    """Scheduler skips disabled jobs."""
    s = _new_scheduler()
    sj = s.add("disabled", interval_seconds=1, task_type="test")
    sj.enabled = False
    sj.next_run_at = sj.created_at
    s.start()
    time.sleep(2)
    s.stop()
    assert sj.last_run_at is None


# --- Endpoint tests ---


def test_create_scheduled_job_endpoint(client, operator_a_headers):
    """POST /scheduled-jobs creates a scheduled job."""
    resp = client.post(
        "/operator/scheduled-jobs",
        json={"name": "cleanup", "interval_seconds": 3600, "task_type": "cleanup"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "cleanup"
    assert data["interval_seconds"] == 3600
    assert data["enabled"] is True


def test_list_scheduled_jobs_endpoint(client, operator_a_headers):
    """GET /scheduled-jobs lists all scheduled jobs."""
    client.post(
        "/operator/scheduled-jobs",
        json={"name": "test", "interval_seconds": 60},
        headers=operator_a_headers,
    )
    resp = client.get(
        "/operator/scheduled-jobs",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["jobs"]) >= 1


def test_get_scheduled_job_endpoint(client, operator_a_headers):
    """GET /scheduled-jobs/{id} returns a scheduled job."""
    create_resp = client.post(
        "/operator/scheduled-jobs",
        json={"name": "test", "interval_seconds": 60},
        headers=operator_a_headers,
    )
    scheduled_id = create_resp.json()["scheduled_id"]

    resp = client.get(
        f"/operator/scheduled-jobs/{scheduled_id}",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "test"


def test_get_scheduled_job_not_found(client, operator_a_headers):
    """GET /scheduled-jobs/{id} returns 404 for unknown."""
    resp = client.get(
        "/operator/scheduled-jobs/nonexistent",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_delete_scheduled_job_endpoint(client, operator_a_headers):
    """DELETE /scheduled-jobs/{id} removes a scheduled job."""
    create_resp = client.post(
        "/operator/scheduled-jobs",
        json={"name": "test", "interval_seconds": 60},
        headers=operator_a_headers,
    )
    scheduled_id = create_resp.json()["scheduled_id"]

    resp = client.delete(
        f"/operator/scheduled-jobs/{scheduled_id}",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    assert resp.json() is True


def test_delete_scheduled_job_not_found(client, operator_a_headers):
    """DELETE /scheduled-jobs/{id} returns 404 for unknown."""
    resp = client.delete(
        "/operator/scheduled-jobs/nonexistent",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_run_scheduled_job_endpoint(client, operator_a_headers):
    """POST /scheduled-jobs/{id}/run triggers a job."""
    create_resp = client.post(
        "/operator/scheduled-jobs",
        json={"name": "test", "interval_seconds": 3600},
        headers=operator_a_headers,
    )
    scheduled_id = create_resp.json()["scheduled_id"]

    resp = client.post(
        f"/operator/scheduled-jobs/{scheduled_id}/run",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    assert "job_id" in resp.json()


def test_run_scheduled_job_not_found(client, operator_a_headers):
    """POST /scheduled-jobs/{id}/run returns 404 for unknown."""
    resp = client.post(
        "/operator/scheduled-jobs/nonexistent/run",
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_scheduled_jobs_requires_auth(client):
    """Scheduled job endpoints require authentication."""
    resp = client.get("/operator/scheduled-jobs")
    assert resp.status_code in (401, 403)
