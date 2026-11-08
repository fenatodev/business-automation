"""SQLite-backed job persistence for the job queue (WP-541).

Provides durable storage for jobs so they survive process restarts.
Uses a single SQLite file with WAL mode for concurrent access.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.job_queue import Job, JobStatus

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"


class JobStore:
    """SQLite persistence layer for Job objects."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL DEFAULT 'generic',
                    company_id INTEGER,
                    payload TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'pending',
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    next_retry_at TEXT,
                    backoff_multiplier REAL NOT NULL DEFAULT 2.0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_id)"
            )

    @staticmethod
    def _job_to_row(job: Job) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "task_type": job.task_type,
            "company_id": job.company_id,
            "payload": json.dumps(job.payload, default=str),
            "status": job.status.value,
            "result": json.dumps(job.result, default=str) if job.result is not None else None,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
            "backoff_multiplier": job.backoff_multiplier,
        }

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        job = Job(
            job_id=row["job_id"],
            task_type=row["task_type"],
            company_id=row["company_id"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            max_retries=row["max_retries"],
            backoff_multiplier=row["backoff_multiplier"],
        )
        job.status = JobStatus(row["status"])
        job.result = json.loads(row["result"]) if row["result"] else None
        job.error = row["error"]
        job.created_at = datetime.fromisoformat(row["created_at"])
        job.started_at = (
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        )
        job.completed_at = (
            datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
        )
        job.retry_count = row["retry_count"]
        job.next_retry_at = (
            datetime.fromisoformat(row["next_retry_at"]) if row["next_retry_at"] else None
        )
        return job

    def save(self, job: Job):
        """Insert or update a job in the store."""
        row = self._job_to_row(job)
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, task_type, company_id, payload, status, result, error,
                    created_at, started_at, completed_at, retry_count, max_retries,
                    next_retry_at, backoff_multiplier
                ) VALUES (
                    :job_id, :task_type, :company_id, :payload, :status, :result, :error,
                    :created_at, :started_at, :completed_at, :retry_count, :max_retries,
                    :next_retry_at, :backoff_multiplier
                )
                ON CONFLICT(job_id) DO UPDATE SET
                    task_type = excluded.task_type,
                    company_id = excluded.company_id,
                    payload = excluded.payload,
                    status = excluded.status,
                    result = excluded.result,
                    error = excluded.error,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    retry_count = excluded.retry_count,
                    max_retries = excluded.max_retries,
                    next_retry_at = excluded.next_retry_at,
                    backoff_multiplier = excluded.backoff_multiplier
                """,
                row,
            )

    def get(self, job_id: str) -> Job | None:
        """Retrieve a job by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def list(
        self,
        company_id: int | None = None,
        status: JobStatus | None = None,
        limit: int = 20,
    ) -> list[Job]:
        """List jobs with optional filtering."""
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list[Any] = []
        if company_id is not None:
            query += " AND company_id = ?"
            params.append(company_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    def delete(self, job_id: str) -> bool:
        """Delete a job by ID. Returns True if deleted."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM jobs WHERE job_id = ?", (job_id,)
            )
        return cursor.rowcount > 0

    def cleanup_completed(self, older_than_seconds: int = 3600) -> int:
        """Remove completed/failed jobs older than the threshold."""
        cutoff = (
            datetime.now(timezone.utc).timestamp() - older_than_seconds
        )
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                DELETE FROM jobs
                WHERE completed_at IS NOT NULL
                  AND completed_at < ?
                  AND status IN ('completed', 'failed')
                """,
                (cutoff_iso,),
            )
        return cursor.rowcount

    def load_all(self) -> list[Job]:
        """Load all jobs from the store."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_job(row) for row in rows]


# Global job store instance
job_store = JobStore()
