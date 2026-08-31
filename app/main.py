from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Lead
from typing import Literal


app = FastAPI(title="Fenato Business Automation API")

Base.metadata.create_all(bind=engine)


class LeadUpdate(BaseModel):
    status: Literal[
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost",
    ]

class LeadCreate(BaseModel):
    name: str
    phone: str
    source: str
    interest: str | None = None


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@app.patch("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    lead.status = data.status

    db.commit()
    db.refresh(lead)

    return lead        


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/leads")
def create_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db),
):
    new_lead = Lead(
        name=lead.name,
        phone=lead.phone,
        source=lead.source,
        interest=lead.interest,
        status="new",
    )

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    return new_lead


@app.get("/leads")
def list_leads(db: Session = Depends(get_db)):
    return db.scalars(
        select(Lead).order_by(Lead.id)
    ).all()


@app.get("/leads/{lead_id}")
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return lead