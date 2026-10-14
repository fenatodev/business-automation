"""Minimal private ASGI entrypoint for the n8n intake pilot.

Mounts only the authenticated evaluation router; no database-backed routers,
operator UI, OpenAPI or docs are exposed by this entrypoint.
"""
from fastapi import FastAPI
from app.routers.commercial_intake import router as commercial_intake_router

app = FastAPI(
    title="Private Commercial Intake",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(commercial_intake_router)
