from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_admin
from app.models import Company
from app.schemas import CompanyCreate


router = APIRouter()


@router.post("/companies")
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    _identity: AccessIdentity = Depends(require_admin),
):
    existing = db.scalar(
        select(Company).where(Company.slug == company.slug)
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Company slug already exists",
        )

    new_company = Company(
        name=company.name,
        slug=company.slug,
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return new_company


@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    _identity: AccessIdentity = Depends(require_admin),
):
    return db.scalars(
        select(Company).order_by(Company.id)
    ).all()
