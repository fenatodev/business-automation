"""In-memory scheduler for periodic jobs (WP-542).

Provides cron-like scheduling for recurring tasks like cleanup,
health checks, and reminders. Uses a background thread to check
and execute scheduled jobs at their intervals.

Supports task handlers for specific task_types:
- "followup": automatically creates follow-up tasks for stale opportunities.
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


def handle_followup_job(payload: dict[str, Any]) -> int:
    """Execute a follow-up job: find stale opportunities and create follow-up tasks.

    This function is called by the scheduler when a "followup" task_type job runs.
    It queries all companies with follow-up config enabled, finds stale opportunities,
    and creates InternalTask records for each.

    Returns the number of follow-up tasks created.
    """
    from app.database import SessionLocal
    from app.models import Company, InternalTask
    from app.services.followup import find_stale_opportunities, get_followup_config
    from sqlalchemy import select
    import uuid as _uuid

    db = SessionLocal()
    created_count = 0

    try:
        # Get all companies with follow-up config enabled
        companies = db.scalars(select(Company)).all()

        for company in companies:
            config = get_followup_config(company.id)
            if not config or not config.enabled:
                continue

            stale = find_stale_opportunities(
                db,
                company.id,
                stale_days=config.stale_days,
            )

            for stale_opp in stale:
                # Deduplicate by opportunity_id in payload
                event_id = f"followup-{stale_opp.opportunity_id}-{stale_opp.days_since_activity}"
                existing = db.scalars(
                    select(InternalTask).where(
                        InternalTask.company_id == company.id,
                        InternalTask.event_id == event_id,
                    )
                ).first()

                if existing is None:
                    task = InternalTask(
                        company_id=company.id,
                        event_id=event_id,
                        payload={
                            "task_type": "followup",
                            "opportunity_id": stale_opp.opportunity_id,
                            "title": stale_opp.title,
                            "days_since_activity": stale_opp.days_since_activity,
                            "next_action": stale_opp.next_action,
                        },
                        status="queued",
                        attempts=0,
                        available_at=datetime.now(timezone.utc),
                    )
                    db.add(task)
                    created_count += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return created_count
