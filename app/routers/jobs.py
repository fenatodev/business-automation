# Job Queue router – expose errors and status

"""API endpoints for accessing job information, especially failures.

- `GET /jobs/{job_id}/error` – retrieve error message for a failed job.
- `GET /jobs` – list jobs (optional filters) – already available via JobQueue but exposed here.
- `GET /jobs/pending-retries` – list jobs scheduled for retry.
- `POST /jobs/{job_id}/retry` – manually retry a failed job.
- `POST /jobs/cleanup` – remove completed/failed jobs older than a threshold.
"""

from fastapi import APIRouter, HTTPException, status
from app.services.job_queue import job_queue, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/", response_model=list)
def list_jobs(company_id: int | None = None, status: JobStatus | None = None, limit: int = 20):
    """List jobs with optional filtering.
    """
    return job_queue.list_jobs(company_id=company_id, status=status, limit=limit)

@router.get("/pending-retries", response_model=list)
def list_pending_retries():
    """List jobs that are scheduled for retry.
    """
    return job_queue.get_pending_retries()

@router.post("/{job_id}/retry", response_model=dict)
def retry_job(job_id: str):
    """Manually retry a failed job.

    Returns the updated job dict.
    """
    try:
        job = job_queue.retry_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return job.__dict__

@router.post("/cleanup", response_model=int)
def cleanup_jobs(older_than_seconds: int = 3600):
    """Remove completed/failed jobs older than the given threshold.

    Returns the number of jobs removed.
    """
    return job_queue.cleanup_completed(older_than_seconds)

@router.get("/{job_id}/error", response_model=str)
def get_job_error(job_id: str):
    """Return the error message for a failed job.

    Returns 404 if job not found or no error.
    """
    job = job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.FAILED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job did not fail")
    if not job.error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No error recorded")
    return job.error