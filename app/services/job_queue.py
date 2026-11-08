"""In-memory job queue for async tasks (WP-532).

Provides a simple job queue with status tracking for async operations
like AI replies, summaries, and other background tasks.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from threading import Thread
from typing import Any, Callable


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    def __init__(
        self,
        job_id: str | None = None,
        task_type: str = "generic",
        company_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ):
        self.job_id = job_id or str(uuid.uuid4())
        self.task_type = task_type
        self.company_id = company_id
        self.payload = payload or {}
        self.status = JobStatus.PENDING
        self.result: Any = None
        self.error: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None


class JobQueue:
    """In-memory job queue with status tracking."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._workers: list[Thread] = []

    def create_job(
        self,
        task_type: str,
        company_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Job:
        """Create a new job and add it to the queue."""
        job = Job(task_type=task_type, company_id=company_id, payload=payload)
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        company_id: int | None = None,
        status: JobStatus | None = None,
        limit: int = 20,
    ) -> list[Job]:
        """List jobs with optional filtering."""
        jobs = list(self._jobs.values())
        if company_id is not None:
            jobs = [j for j in jobs if j.company_id == company_id]
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def execute_job(
        self,
        job_id: str,
        func: Callable[..., Any],
        *,
        _async: bool = True,
    ) -> Job:
        """Execute a job synchronously or asynchronously."""
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")

        if not _async:
            return self._run_job(job, func)

        thread = Thread(target=self._run_job, args=(job, func), daemon=True)
        self._workers.append(thread)
        thread.start()
        return job

    def _run_job(self, job: Job, func: Callable[..., Any]) -> Job:
        """Run a job function and update status."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        try:
            job.result = func(**job.payload)
            job.status = JobStatus.COMPLETED
        except Exception as exc:
            job.error = str(exc)
            job.status = JobStatus.FAILED
        finally:
            job.completed_at = datetime.now(timezone.utc)
        return job

    def cleanup_completed(self, older_than_seconds: int = 3600) -> int:
        """Remove completed/failed jobs older than the threshold."""
        cutoff = datetime.now(timezone.utc).timestamp() - older_than_seconds
        to_remove = [
            jid
            for jid, job in self._jobs.items()
            if job.completed_at
            and job.completed_at.timestamp() < cutoff
        ]
        for jid in to_remove:
            del self._jobs[jid]
        return len(to_remove)


# Global job queue instance
job_queue = JobQueue()
