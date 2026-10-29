"""Commercial pipeline service — WP-058 synthetic pilot.

Orchestrates the full flow: intake → triage → draft → review queue → decision.
Uses only the existing intake engine; no external calls, no real messages sent.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ReviewQueueItem
from app.schemas import ReviewQueueTrigger
from app.services.commercial_intake import (
    CandidateReply,
    CommercialIntakeEvent,
    IntakeDecision,
    process_commercial_intake,
)

logger = logging.getLogger(__name__)


def _build_intake_event(
    trigger: ReviewQueueTrigger,
    company_id: int,
    service_context: str,
) -> CommercialIntakeEvent:
    """Convert a review queue trigger into a CommercialIntakeEvent."""
    return CommercialIntakeEvent(
        channel=trigger.channel,
        message=trigger.message,
        service_context=service_context,
        event_id=trigger.event_id,
    )


def triage_and_queue(
    db: Session,
    trigger: ReviewQueueTrigger,
    company_id: int,
    service_context: str,
) -> ReviewQueueItem:
    """Run intake triage and persist the result in the review queue.

    If an item with the same (company_id, event_id) already exists, returns
    the existing row without re-processing (idempotency).

    Args:
        db: SQLAlchemy session.
        trigger: Validated intake trigger data.
        company_id: Tenant company ID derived from authenticated identity.
        service_context: Server-side service context string.

    Returns:
        The (new or existing) ReviewQueueItem row.
    """
    # Check idempotency first
    existing = db.scalar(
        select(ReviewQueueItem).where(
            ReviewQueueItem.company_id == company_id,
            ReviewQueueItem.event_id == trigger.event_id,
        )
    )
    if existing is not None:
        logger.info(
            "Review queue item already exists (idempotent): event_id=%s",
            trigger.event_id,
        )
        return existing

    # Triage via intake engine
    event = _build_intake_event(trigger, company_id, service_context)
    decision: IntakeDecision = process_commercial_intake(
        event,
        candidate=CandidateReply(text=""),
    )

    # Persist in review queue
    item = ReviewQueueItem(
        company_id=company_id,
        event_id=trigger.event_id,
        channel=trigger.channel,
        message=trigger.message,
        intent=decision.intent if decision.intent != "unknown" else None,
        draft_reply=decision.draft_reply or None,
        status="pending",
        needs_human_review=decision.needs_human_review,
        flags_json={
            "intent": decision.intent,
            "next_step": decision.next_step,
            "flags": decision.flags,
        } if decision.flags else None,
    )
    db.add(item)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Race condition: another request created the same event_id
        existing = db.scalar(
            select(ReviewQueueItem).where(
                ReviewQueueItem.company_id == company_id,
                ReviewQueueItem.event_id == trigger.event_id,
            )
        )
        if existing is not None:
            return existing
        raise

    db.refresh(item)
    return item


def apply_decision(
    db: Session,
    item_id: int,
    company_id: int,
    decision: str,
    operator_note: str | None = None,
) -> ReviewQueueItem:
    """Apply an operator decision (approve/reject) to a review queue item.

    Args:
        db: SQLAlchemy session.
        item_id: Review queue item ID.
        company_id: Tenant company ID for isolation.
        decision: "approve" or "reject".
        operator_note: Optional operator comment.

    Returns:
        Updated ReviewQueueItem.

    Raises:
        ValueError: If item not found, wrong tenant, or already decided.
    """
    item = db.scalar(
        select(ReviewQueueItem).where(
            ReviewQueueItem.id == item_id,
            ReviewQueueItem.company_id == company_id,
        )
    )
    if item is None:
        raise ValueError("Review queue item not found")

    if item.status != "pending":
        raise ValueError(f"Item already decided: status={item.status}")

    item.status = decision
    item.operator_note = operator_note
    db.commit()
    db.refresh(item)
    return item


def list_pending_items(
    db: Session,
    company_id: int,
) -> list[ReviewQueueItem]:
    """Return all pending review queue items for a tenant."""
    return db.scalars(
        select(ReviewQueueItem)
        .where(
            ReviewQueueItem.company_id == company_id,
            ReviewQueueItem.status == "pending",
        )
        .order_by(ReviewQueueItem.created_at)
    ).all()


def get_item(
    db: Session,
    item_id: int,
    company_id: int,
) -> ReviewQueueItem | None:
    """Return a single review queue item if it belongs to the tenant."""
    return db.scalar(
        select(ReviewQueueItem).where(
            ReviewQueueItem.id == item_id,
            ReviewQueueItem.company_id == company_id,
        )
    )
