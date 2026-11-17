# Scheduler router – expose control over in‑memory Scheduler

"""API for managing scheduled jobs.

- `GET /scheduler/` – list scheduled jobs.
- `POST /scheduler/` – create a new scheduled job.
- `PATCH /scheduler/{scheduled_id}/cancel` – cancel a scheduled job.
- `POST /scheduler/{scheduled_id}/toggle` – enable/disable a scheduled job.
- `POST /scheduler/{scheduled_id}/run-now` – trigger a scheduled job immediately.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import AccessIdentity
from app.dependencies import require_operator
from app.schemas import ScheduledJobCreate, ScheduledJobStatus
from app.services.scheduler import scheduler, ScheduledJob

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

@router.get("/", response_model=list[ScheduledJobStatus])
def list_scheduled_jobs(
    _identity: AccessIdentity = Depends(require_operator),
):
    """Return all scheduled jobs as structured responses."""
    return [
        ScheduledJobStatus(
            scheduled_id=job.scheduled_id,
            name=job.name,
            interval_seconds=job.interval_seconds,
            task_type=job.task_type,
            enabled=job.enabled,
            last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
            next_run_at=job.next_run_at.isoformat() if job.next_run_at else None,
            last_job_id=job.last_job_id,
            last_status=job.last_status,
            last_error=job.last_error,
        )
        for job in scheduler.list()
    ]


@router.post("/", response_model=ScheduledJobStatus, status_code=status.HTTP_201_CREATED)
def create_scheduled_job(
    data: ScheduledJobCreate,
    _identity: AccessIdentity = Depends(require_operator),
):
    """Create a new scheduled job.

    The task_type can be "followup" to automatically create follow-up tasks
    for stale opportunities, or "scheduled" for generic tasks.
    """
    job = scheduler.add(
        name=data.name,
        interval_seconds=data.interval_seconds,
        task_type=data.task_type,
        payload=data.payload,
    )
    return ScheduledJobStatus(
        scheduled_id=job.scheduled_id,
        name=job.name,
        interval_seconds=job.interval_seconds,
        task_type=job.task_type,
        enabled=job.enabled,
        last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
        next_run_at=job.next_run_at.isoformat() if job.next_run_at else None,
        last_job_id=job.last_job_id,
        last_status=job.last_status,
        last_error=job.last_error,
    )


@router.patch("/{scheduled_id}/cancel", response_model=bool)
def cancel_scheduled_job(
    scheduled_id: str,
    _identity: AccessIdentity = Depends(require_operator),
):
    """Cancel (remove) a scheduled job.

    Returns ``True`` if the job existed and was removed, ``False`` otherwise.
    """
    cancelled = scheduler.remove(scheduled_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled job {scheduled_id} not found",
        )
    return True


@router.post("/{scheduled_id}/toggle", response_model=ScheduledJobStatus)
def toggle_scheduled_job(
    scheduled_id: str,
    enabled: bool,
    _identity: AccessIdentity = Depends(require_operator),
):
    """Enable or disable a scheduled job.

    Returns the updated job as structured response.
    """
    job = scheduler.toggle(scheduled_id, enabled)
    if job is None:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return ScheduledJobStatus(
        scheduled_id=job.scheduled_id,
        name=job.name,
        interval_seconds=job.interval_seconds,
        task_type=job.task_type,
        enabled=job.enabled,
        last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
        next_run_at=job.next_run_at.isoformat() if job.next_run_at else None,
        last_job_id=job.last_job_id,
        last_status=job.last_status,
        last_error=job.last_error,
    )


@router.post("/{scheduled_id}/run-now", response_model=dict | None)
def run_scheduled_job_now(
    scheduled_id: str,
    _identity: AccessIdentity = Depends(require_operator),
):
    """Trigger a scheduled job immediately.

    Returns the created job dict or None if the scheduled job was not found.
    """
    from app.services.job_queue import Job

    job = scheduler.run_now(scheduled_id)
    if job is None:
        return None
    return {"job_id": job.job_id, "task_type": job.task_type}

@router.post("/start", response_model=bool)
def start_scheduler(
    _identity: AccessIdentity = Depends(require_operator),
):
    """Start the background scheduler thread.

    Returns ``True`` if started, ``False`` if already running.
    """
    if hasattr(scheduler, "_running") and scheduler._running:
        return False
    scheduler.start()
    return True


@router.post("/stop", response_model=bool)
def stop_scheduler(
    _identity: AccessIdentity = Depends(require_operator),
):
    """Stop the background scheduler thread.

    Returns ``True`` if stopped, ``False`` if it was not running.
    """
    if not (hasattr(scheduler, "_running") and scheduler._running):
        return False
    scheduler.stop()
    return True
