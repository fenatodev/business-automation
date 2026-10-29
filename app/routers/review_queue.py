"""Review queue router — WP-058 commercial pilot.

Provides endpoints for the human operator to manage the commercial review queue:
trigger synthetic intake events, list pending items, and make approve/reject decisions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.database import settings
from app.dependencies import get_db, require_operator
from app.schemas import (
    ReviewQueueDecision,
    ReviewQueueItemOut,
    ReviewQueueTrigger,
)
from app.services import commercial_pipeline as pipeline

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


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
def list_pending_review_items(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> list[ReviewQueueItemOut]:
    """List all pending review queue items for the authenticated tenant."""
    items = pipeline.list_pending_items(db, identity.company_id)
    return [ReviewQueueItemOut.model_validate(item) for item in items]


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
    response_model=ReviewQueueItemOut,
)
def apply_review_decision(
    item_id: int,
    decision_data: ReviewQueueDecision,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> ReviewQueueItemOut:
    """Apply an operator decision (approve/reject) to a review queue item."""
    try:
        item = pipeline.apply_decision(
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
    return ReviewQueueItemOut.model_validate(item)
