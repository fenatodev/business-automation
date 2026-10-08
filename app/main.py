from fastapi import FastAPI

from app.dependencies import get_db
from app.routers.companies import router as companies_router
from app.routers.conversations import router as conversations_router
from app.routers.customers import router as customers_router
from app.routers.leads import router as leads_router
from app.routers.opportunities import router as opportunities_router
from app.routers.operator_ui import router as operator_ui_router


app = FastAPI(
    title="Fenato Business Automation API",
    version="0.1.0",
)

app.include_router(companies_router)
app.include_router(conversations_router)
app.include_router(customers_router)
app.include_router(leads_router)
app.include_router(opportunities_router)
app.include_router(operator_ui_router)


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Fenato Business Automation API",
        "status": "running",
    }
