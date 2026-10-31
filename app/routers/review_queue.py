"""Review queue router — WP-058 commercial pilot.

Provides endpoints for the human operator to manage the commercial review queue:
trigger synthetic intake events, list pending items, and make approve/reject decisions.
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.database import settings
from app.dependencies import get_db, require_operator
from app.schemas import (
    ReviewQueueDecision,
    ReviewQueueDecisionResponse,
    ReviewQueueItemOut,
    ReviewQueueTrigger,
)
from app.models import ReviewQueueItem
from app.services import commercial_pipeline as pipeline

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


@router.get("/export.csv")
def export_review_queue_csv(
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export review queue items for the authenticated tenant as CSV, respecting filters."""
    query = select(ReviewQueueItem).where(ReviewQueueItem.company_id == identity.company_id)
    if status:
        query = query.where(ReviewQueueItem.status == status)
    items = db.scalars(query.order_by(ReviewQueueItem.id)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Evento", "Canal", "Mensagem", "Intenção",
        "Rascunho", "Status", "Nota operador", "Revisão humana",
        "Flags", "Criada em",
    ])
    for item in items:
        writer.writerow([
            item.id,
            item.event_id,
            item.channel or "",
            item.message or "",
            item.intent or "",
            item.draft_reply or "",
            item.status,
            item.operator_note or "",
            item.needs_human_review,
            item.flags_json or "",
            item.created_at.isoformat() if item.created_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=review-queue.csv",
        },
    )


@router.post(
    "/synthetic-trigger",
    response_model=ReviewQueueItemOut,
    status_code=status.HTTP_201_CREATED,
)
def trigger_synthetic_intake(
    trigger: ReviewQueueTrigger,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> ReviewQueueItemOut:
    """Trigger a synthetic commercial intake event and queue it for review.

    Idempotent: the same event_id for the same tenant returns the existing item.
    """
    item = pipeline.triage_and_queue(
        db=db,
        trigger=trigger,
        company_id=identity.company_id,
        service_context=settings.intake_service_context,
    )
    return ReviewQueueItemOut.model_validate(item)


@router.get("/", response_model=list[ReviewQueueItemOut])
def list_review_items(
    status: str | None = Query(None, description="Filter by status: pending, approved, rejected (default: pending)"),
    sort: str = Query(default="created_at", description="Sort by: id, created_at, status"),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> list[ReviewQueueItemOut]:
    """List review queue items for the authenticated tenant with optional filters.

    Defaults to pending items only for backward compatibility.
    """
    stmt = select(ReviewQueueItem).where(ReviewQueueItem.company_id == identity.company_id)
    if status is not None:
        stmt = stmt.where(ReviewQueueItem.status == status)
    else:
        # Default to pending for backward compatibility
        stmt = stmt.where(ReviewQueueItem.status == "pending")
    if sort == "created_at":
        stmt = stmt.order_by(desc(ReviewQueueItem.created_at), ReviewQueueItem.id)
    elif sort == "status":
        stmt = stmt.order_by(ReviewQueueItem.status, ReviewQueueItem.id)
    else:
        stmt = stmt.order_by(ReviewQueueItem.id)
    stmt = stmt.offset(offset).limit(limit)
    items = db.scalars(stmt).all()
    return [ReviewQueueItemOut.model_validate(item) for item in items]


@router.get("/count")
def count_review_items(
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> dict[str, int]:
    """Count review queue items with optional status filter."""
    stmt = select(func.count()).select_from(ReviewQueueItem).where(
        ReviewQueueItem.company_id == identity.company_id
    )
    if status is not None:
        stmt = stmt.where(ReviewQueueItem.status == status)
    total = db.scalar(stmt)
    return {"total": total}


@router.get("/summary", response_model=dict[str, int])
def get_review_queue_summary(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> dict[str, int]:
    """Return tenant-scoped counts; no message content or PII."""
    return pipeline.review_queue_summary(db, identity.company_id)


@router.get("/aging", response_model=dict[str, int])
def get_review_queue_aging(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> dict[str, int]:
    """Show stale pending work without exposing messages or customer data."""
    return pipeline.review_queue_aging(db, identity.company_id)


@router.get("/{item_id}", response_model=ReviewQueueItemOut)
def get_review_item(
    item_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> ReviewQueueItemOut:
    """Get a single review queue item by ID."""
    item = pipeline.get_item(db, item_id, identity.company_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review queue item not found",
        )
    return ReviewQueueItemOut.model_validate(item)


@router.patch(
    "/{item_id}/decision",
    response_model=ReviewQueueDecisionResponse,
)
def apply_review_decision(
    item_id: int,
    decision_data: ReviewQueueDecision,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> ReviewQueueDecisionResponse:
    """Apply an operator decision (approve/reject) to a review queue item.

    Returns the updated item along with the created opportunity_id (if approved).
    """
    try:
        item, created_opportunity = pipeline.apply_decision(
            db=db,
            item_id=item_id,
            company_id=identity.company_id,
            decision=decision_data.decision,
            operator_note=decision_data.operator_note,
        )
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review queue item not found",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return ReviewQueueDecisionResponse(
        id=item.id,
        company_id=item.company_id,
        event_id=item.event_id,
        channel=item.channel,
        message=item.message,
        intent=item.intent,
        draft_reply=item.draft_reply,
        status=item.status,
        operator_note=item.operator_note,
        needs_human_review=item.needs_human_review,
        flags_json=item.flags_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
        opportunity_id=created_opportunity.id if created_opportunity is not None else None,
    )
