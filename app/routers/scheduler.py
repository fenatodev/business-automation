# Scheduler router – expose control over in‑memory Scheduler

"""API for managing scheduled jobs.

- `GET /scheduler/` – list scheduled jobs.
- `PATCH /scheduler/{scheduled_id}/cancel` – cancel a scheduled job.
- `POST /scheduler/{scheduled_id}/toggle` – enable/disable a scheduled job.
- `POST /scheduler/{scheduled_id}/run-now` – trigger a scheduled job immediately.
"""

from fastapi import APIRouter, HTTPException, status
from app.services.scheduler import scheduler, ScheduledJob

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

@router.get("/", response_model=list[dict])
def list_scheduled_jobs():
    """Return all scheduled jobs as dicts."""
    return [job.__dict__ for job in scheduler.list()]

@router.patch("/{scheduled_id}/cancel", response_model=bool)
def cancel_scheduled_job(scheduled_id: str):
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

@router.post("/{scheduled_id}/toggle", response_model=dict)
def toggle_scheduled_job(scheduled_id: str, enabled: bool):
    """Enable or disable a scheduled job.

    Returns the updated job as dict.
    """
    job = scheduler.toggle(scheduled_id, enabled)
    if job is None:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return job.__dict__

@router.post("/start", response_model=bool)
def start_scheduler():
    """Start the background scheduler thread.

    Returns ``True`` if started, ``False`` if already running.
    """
    if hasattr(scheduler, "_running") and scheduler._running:
        return False
    scheduler.start()
    return True

@router.post("/stop", response_model=bool)
def stop_scheduler():
    """Stop the background scheduler thread.

    Returns ``True`` if stopped, ``False`` if it was not running.
    """
    if not (hasattr(scheduler, "_running") and scheduler._running):
        return False
    scheduler.stop()
    return True
