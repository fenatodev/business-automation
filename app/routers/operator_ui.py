"""Página interna de operação privada: somente arquivos estáticos, sem dados.

O acesso aos dados continua exclusivamente pelas APIs Bearer existentes.
Essa página não faz login, não altera auth e não concede acesso tenant.
"""

from pathlib import Path
import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.dependencies import require_operator
from app.dependencies import AccessIdentity
from app.schemas import JobCreate, JobListResponse, JobRetryConfig, JobStatusResponse


router = APIRouter(prefix="/operator", include_in_schema=False)

_ASSETS = Path(__file__).resolve().parents[1] / "operator_ui"
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver"}

_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; form-action 'self'; base-uri 'none'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
    "Cross-Origin-Resource-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _local_only(request: Request) -> None:
    client = request.client
    hostname = request.url.hostname
    # TestClient usa client=testclient, host=testserver.
    if client is not None and client.host == "testclient":
        if hostname == "testserver":
            return
    else:
        try:
            is_loopback = client is not None and ipaddress.ip_address(
                client.host
            ).is_loopback
        except ValueError:
            is_loopback = False
        if is_loopback and hostname in _ALLOWED_HOSTS - {"testserver"}:
            return

    raise HTTPException(status_code=404, detail="Not found")


def _static_response(request: Request, filename: str, media_type: str):
    _local_only(request)
    return FileResponse(
        _ASSETS / filename,
        media_type=media_type,
        headers=_HEADERS,
    )


@router.get("")
def operator_page(request: Request):
    return _static_response(request, "index.html", "text/html")


@router.get("/app.js")
def operator_script(request: Request):
    return _static_response(request, "app.js", "text/javascript")


@router.get("/styles.css")
def operator_styles(request: Request):
    return _static_response(request, "styles.css", "text/css")


# ---------------------------------------------------------------------------
# WP-532 — Job queue endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=JobStatusResponse)
def create_job(
    data: JobCreate,
    identity: AccessIdentity = Depends(require_operator),
):
    """Create a new async job."""
    from app.services.job_queue import job_queue

    job = job_queue.create_job(
        task_type=data.task_type,
        company_id=identity.company_id,
        payload=dict(data.payload),
        max_retries=data.max_retries,
        backoff_multiplier=data.backoff_multiplier,
    )
    return _job_to_response(job)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    identity: AccessIdentity = Depends(require_operator),
):
    """Get job status by ID."""
    from app.services.job_queue import job_queue

    job = job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.company_id and job.company_id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _job_to_response(job)


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    limit: int = 20,
    identity: AccessIdentity = Depends(require_operator),
):
    """List recent jobs for this company."""
    from app.services.job_queue import JobStatus, job_queue

    jobs = job_queue.list_jobs(
        company_id=identity.company_id,
        limit=min(limit, 100),
    )
    return JobListResponse(jobs=[_job_to_response(j) for j in jobs])


def _job_to_response(job) -> JobStatusResponse:
    """Convert a Job to JobStatusResponse."""
    return JobStatusResponse(
        job_id=job.job_id,
        task_type=job.task_type,
        status=job.status.value,
        result=job.result,
        error=job.error,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        retry_count=getattr(job, "retry_count", 0),
        max_retries=getattr(job, "max_retries", 3),
        next_retry_at=(
            job.next_retry_at.isoformat() if getattr(job, "next_retry_at", None) else None
        ),
    )


# WP-535 health check moved to companies router (no _local_only restriction)


# ---------------------------------------------------------------------------
# WP-540 — Job retry endpoint
# ---------------------------------------------------------------------------


@router.post("/jobs/{job_id}/retry", response_model=JobStatusResponse)
def retry_job(
    job_id: str,
    identity: AccessIdentity = Depends(require_operator),
):
    """Manually retry a failed job."""
    from app.services.job_queue import job_queue

    job = job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.company_id and job.company_id != identity.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        job_queue.retry_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _job_to_response(job_queue.get_job(job_id))
