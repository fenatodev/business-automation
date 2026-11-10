# Scheduler router – expose control over in‑memory Scheduler

"""API for managing scheduled jobs.

Provides:
- `PATCH /scheduler/{scheduled_id}/cancel` – cancel a scheduled job.
- `GET /scheduler` – list scheduled jobs (already available via Scheduler instance, but
  exposed for observability).
"""

from fastapi import APIRouter, Depends, HTTPException, status
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
