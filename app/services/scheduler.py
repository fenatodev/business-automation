"""In-memory scheduler for periodic jobs (WP-542).

Provides cron-like scheduling for recurring tasks like cleanup,
health checks, and reminders. Uses a background thread to check
and execute scheduled jobs at their intervals.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from typing import Any, Callable

from app.services.job_queue import Job, JobQueue, JobStatus


class ScheduledJob:
    """A recurring job that runs at a fixed interval."""

    def __init__(
        self,
        name: str,
        interval_seconds: int,
        task_type: str = "scheduled",
        payload: dict[str, Any] | None = None,
        enabled: bool = True,
    ):
        self.scheduled_id = str(uuid.uuid4())
        self.name = name
        self.interval_seconds = interval_seconds
        self.task_type = task_type
        self.payload = payload or {}
        self.enabled = enabled
        self.last_run_at: datetime | None = None
        self.next_run_at: datetime | None = None
        self.created_at = datetime.now(timezone.utc)
        self.last_job_id: str | None = None
        self.last_status: str | None = None
        self.last_error: str | None = None

    def __repr__(self):
        return f"ScheduledJob({self.name!r}, interval={self.interval_seconds}s)"


class Scheduler:
    """In-memory scheduler that runs jobs at fixed intervals."""

    def __init__(self, job_queue: JobQueue | None = None):
        from app.services.job_queue import job_queue as default_queue
        self._queue = job_queue or default_queue
        self._scheduled: dict[str, ScheduledJob] = {}
        self._running = False
        self._stop_event: Event | None = None
        self._worker: Thread | None = None

    def add(
        self,
        name: str,
        interval_seconds: int,
        task_type: str = "scheduled",
        payload: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        """Add a new scheduled job."""
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be >= 1")
        job = ScheduledJob(
            name=name,
            interval_seconds=interval_seconds,
            task_type=task_type,
            payload=payload,
        )
        self._scheduled[job.scheduled_id] = job
        return job

    def get(self, scheduled_id: str) -> ScheduledJob | None:
        """Get a scheduled job by ID."""
        return self._scheduled.get(scheduled_id)

    def list(self) -> list[ScheduledJob]:
        """List all scheduled jobs."""
        return list(self._scheduled.values())

    def remove(self, scheduled_id: str) -> bool:
        """Remove a scheduled job. Returns True if removed."""
        return self._scheduled.pop(scheduled_id, None) is not None

    def toggle(self, scheduled_id: str, enabled: bool) -> ScheduledJob | None:
        """Toggle a scheduled job on/off."""
        job = self._scheduled.get(scheduled_id)
        if job is None:
            return None
        job.enabled = enabled
        return job

    def start(self):
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._stop_event = Event()
        self._worker = Thread(target=self._loop, daemon=True)
        self._worker.start()

    def stop(self):
        """Stop the scheduler background thread."""
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=5)
        self._worker = None

    def _loop(self):
        """Main scheduler loop."""
        while self._running and not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            for job in list(self._scheduled.values()):
                if not job.enabled:
                    continue
                if job.next_run_at is None or job.next_run_at <= now:
                    self._execute(job)
            # Sleep briefly to avoid busy-waiting
            self._stop_event.wait(timeout=1)

    def _execute(self, job: ScheduledJob):
        """Execute a scheduled job."""
        try:
            j = self._queue.create_job(
                task_type=job.task_type,
                payload=dict(job.payload),
            )
            job.last_job_id = j.job_id
            job.last_run_at = datetime.now(timezone.utc)
            job.next_run_at = job.last_run_at + timedelta(
                seconds=job.interval_seconds
            )
            job.last_status = None
            job.last_error = None
        except Exception as exc:
            job.last_error = str(exc)

    def run_now(self, scheduled_id: str) -> Job | None:
        """Manually trigger a scheduled job immediately."""
        job = self._scheduled.get(scheduled_id)
        if job is None:
            return None
        try:
            j = self._queue.create_job(
                task_type=job.task_type,
                payload=dict(job.payload),
            )
            job.last_job_id = j.job_id
            job.last_run_at = datetime.now(timezone.utc)
            return j
        except Exception:
            return None


# Global scheduler instance
scheduler = Scheduler()
