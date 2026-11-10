from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.observability import RequestObservabilityMiddleware

from app.routers.internal_tasks import router as internal_tasks_router
from app.dependencies import get_db
from app.routers.commercial_intake import router as commercial_intake_router
from app.routers.companies import router as companies_router
from app.routers.conversations import router as conversations_router
from app.routers.customers import router as customers_router
from app.routers.leads import router as leads_router
from app.routers.opportunities import router as opportunities_router
from app.routers.operator_ui import router as operator_ui_router
from app.routers.review_queue import router as review_queue_router
from app.routers.scheduler import router as scheduler_router
from app.routers.jobs import router as jobs_router
from app.database import SessionLocal


app = FastAPI(
    title="Fenato Business Automation API",
    version="0.1.0",
)
app.add_middleware(RequestObservabilityMiddleware)

app.include_router(commercial_intake_router)
app.include_router(companies_router)
app.include_router(conversations_router)
app.include_router(customers_router)
app.include_router(leads_router)
app.include_router(opportunities_router)
app.include_router(operator_ui_router)
app.include_router(review_queue_router)
app.include_router(scheduler_router)
app.include_router(jobs_router)


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Fenato Business Automation API",
        "status": "running",
    }


@app.get("/health")
def health(response: Response):
    """Stable liveness contract for local operators and process supervisors."""
    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok", "service": "business-automation"}


@app.get("/healthz")
def healthz(response: Response):
    """Kubernetes-style alias for the stable liveness contract."""
    return health(response)


@app.get("/readiness")
def readiness(response: Response):
    """Check database readiness without exposing connection details."""
    response.headers["Cache-Control"] = "no-store"
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unready"})
    finally:
        db.close()
    return {"status": "ready", "service": "business-automation"}


@app.get("/readyz")
def readyz(response: Response):
    """Kubernetes-style alias for the database readiness contract."""
    return readiness(response)
