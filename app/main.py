from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Fenato Business Automation API")


class LeadCreate(BaseModel):
    name: str
    phone: str
    source: str
    interest: str | None = None


leads = []


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/leads")
def create_lead(lead: LeadCreate):
    new_lead = {
        "id": len(leads) + 1,
        **lead.model_dump(),
        "status": "new",
    }

    leads.append(new_lead)

    return new_lead


@app.get("/leads")
def list_leads():
    return leads