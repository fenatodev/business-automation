"""WP-550 — Scheduler integration with follow-up for stale opportunities.

Tests that the scheduler can create scheduled jobs for follow-up tasks,
and that the API endpoints are properly authenticated.
"""
from app.services.followup import (
    _followup_configs,
)
from app.services.scheduler import (
    ScheduledJob,
    scheduler,
    handle_followup_job,
)


def _reset_configs():
    _followup_configs.clear()


def _reset_scheduler():
    """Clear all scheduled jobs."""
    for job in list(scheduler.list()):
        scheduler.remove(job.scheduled_id)


# --- Scheduler API endpoint tests ---


class TestSchedulerEndpoints:
    """Test scheduler API endpoints."""

    def setup_method(self):
        _reset_scheduler()

    def test_create_scheduled_job(self, client, operator_a_headers):
        """POST /scheduler/ creates a new scheduled job."""
        resp = client.post(
            "/scheduler/",
            json={
                "name": "followup-check",
                "interval_seconds": 3600,
                "task_type": "followup",
                "payload": {},
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "followup-check"
        assert data["task_type"] == "followup"
        assert data["interval_seconds"] == 3600
        assert data["enabled"] is True
        assert "scheduled_id" in data

    def test_list_scheduled_jobs(self, client, operator_a_headers):
        """GET /scheduler/ returns scheduled jobs."""
        # Create a job first
        client.post(
            "/scheduler/",
            json={
                "name": "test-job",
                "interval_seconds": 60,
                "task_type": "scheduled",
            },
            headers=operator_a_headers,
        )

        resp = client.get("/scheduler/", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(j["name"] == "test-job" for j in data)

    def test_create_scheduled_job_requires_auth(self, client):
        """POST /scheduler/ requires authentication."""
        resp = client.post(
            "/scheduler/",
            json={
                "name": "unauthorized-job",
                "interval_seconds": 60,
            },
        )
        assert resp.status_code in (401, 403)

    def test_list_scheduled_jobs_requires_auth(self, client):
        """GET /scheduler/ requires authentication."""
        resp = client.get("/scheduler/")
        assert resp.status_code in (401, 403)

    def test_cancel_scheduled_job(self, client, operator_a_headers):
        """PATCH /scheduler/{id}/cancel removes a job."""
        create_resp = client.post(
            "/scheduler/",
            json={
                "name": "to-cancel",
                "interval_seconds": 60,
            },
            headers=operator_a_headers,
        )
        scheduled_id = create_resp.json()["scheduled_id"]

        resp = client.patch(
            f"/scheduler/{scheduled_id}/cancel",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json() is True

    def test_toggle_scheduled_job(self, client, operator_a_headers):
        """POST /scheduler/{id}/toggle enables/disables a job."""
        create_resp = client.post(
            "/scheduler/",
            json={
                "name": "to-toggle",
                "interval_seconds": 60,
            },
            headers=operator_a_headers,
        )
        scheduled_id = create_resp.json()["scheduled_id"]

        resp = client.post(
            f"/scheduler/{scheduled_id}/toggle?enabled=false",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_run_now_scheduled_job(self, client, operator_a_headers):
        """POST /scheduler/{id}/run-now triggers a job immediately."""
        create_resp = client.post(
            "/scheduler/",
            json={
                "name": "run-now-test",
                "interval_seconds": 86400,
                "task_type": "scheduled",
            },
            headers=operator_a_headers,
        )
        scheduled_id = create_resp.json()["scheduled_id"]

        resp = client.post(
            f"/scheduler/{scheduled_id}/run-now",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert "job_id" in data
