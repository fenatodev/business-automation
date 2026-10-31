"""Commercial pipeline service — WP-058 synthetic pilot.

Orchestrates the full flow: intake → triage → draft → review queue → decision.
Uses only the existing intake engine; no external calls, no real messages sent.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import logging
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Opportunity, ReviewQueueItem
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


def build_review_item(
    trigger: ReviewQueueTrigger, company_id: int, service_context: str,
) -> ReviewQueueItem:
    """Build a deterministic internal result without database or external effects."""
    # Triage via intake engine
    event = _build_intake_event(trigger, company_id, service_context)
    decision: IntakeDecision = process_commercial_intake(
        event,
        candidate=CandidateReply(text=""),
    )

    return ReviewQueueItem(
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

    item = build_review_item(trigger, company_id, service_context)
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


def _create_opportunity_from_review(
    db: Session,
    item: ReviewQueueItem,
    company_id: int,
) -> Opportunity | None:
    """Create an Opportunity from an approved review queue item.

    Returns the created Opportunity, or None if one already exists for this event_id.
    """
    # Deduplication: check if opportunity already exists for this event_id
    existing = db.scalar(
        select(Opportunity).where(
            Opportunity.company_id == company_id,
            Opportunity.source == "review_queue",
            Opportunity.external_url == f"review://{item.event_id}",
        )
    )
    if existing is not None:
        return existing

    title = (
        f"Review: {item.intent}"
        if item.intent
        else "Oportunidade de review"
    )
    description = item.message or ""
    if item.draft_reply:
        description += f"\n\n[Rascunho: {item.draft_reply}]"
    if item.operator_note:
        description += f"\n\n[Nota do operador: {item.operator_note}]"

    opp = Opportunity(
        company_id=company_id,
        source="review_queue",
        external_url=f"review://{item.event_id}",
        title=title,
        description=description[:2000],
        captured_at=datetime.now(timezone.utc),
    )
    db.add(opp)
    try:
        db.commit()
        db.refresh(opp)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Opportunity).where(
                Opportunity.company_id == company_id,
                Opportunity.source == "review_queue",
                Opportunity.external_url == f"review://{item.event_id}",
            )
        )
        return existing
    return opp


def apply_decision(
    db: Session,
    item_id: int,
    company_id: int,
    decision: str,
    operator_note: str | None = None,
) -> ReviewQueueItem:
    """Apply an operator decision (approve/reject) to a review queue item.

    When approved, automatically creates an Opportunity for follow-up.

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
    result = db.execute(
        update(ReviewQueueItem)
        .where(
            ReviewQueueItem.id == item_id,
            ReviewQueueItem.company_id == company_id,
            ReviewQueueItem.status == "pending",
        )
        .values(status=decision, operator_note=operator_note)
    )
    if result.rowcount != 1:
        db.rollback()
        existing = db.scalar(
            select(ReviewQueueItem.status).where(
                ReviewQueueItem.id == item_id,
                ReviewQueueItem.company_id == company_id,
            )
        )
        if existing is None:
            raise ValueError("Review queue item not found")
        raise ValueError(f"Item already decided: status={existing}")

    # WP-097: create opportunity on approve
    if decision == "approve":
        item = db.get(ReviewQueueItem, item_id)
        if item is not None:
            _create_opportunity_from_review(db, item, company_id)
    else:
        db.commit()

    item = db.get(ReviewQueueItem, item_id)
    db.refresh(item)
    return item


def list_pending_items(
    db: Session,
    company_id: int,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[ReviewQueueItem]:
    """Return all pending review queue items for a tenant."""
    return db.scalars(
        select(ReviewQueueItem)
        .where(
            ReviewQueueItem.company_id == company_id,
            ReviewQueueItem.status == "pending",
        )
        .order_by(ReviewQueueItem.created_at, ReviewQueueItem.id)
        .offset(offset)
        .limit(limit)
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


def review_queue_summary(db: Session, company_id: int) -> dict[str, int]:
    """Count operator queue states within the authenticated tenant only."""
    rows = db.execute(
        select(ReviewQueueItem.status, func.count(ReviewQueueItem.id))
        .where(ReviewQueueItem.company_id == company_id)
        .group_by(ReviewQueueItem.status)
    ).all()
    counts = {"pending": 0, "approve": 0, "reject": 0}
    for state, count in rows:
        if state in counts:
            counts[state] = int(count)
    return counts


def review_queue_aging(db: Session, company_id: int, *, older_than_hours: int = 24) -> dict[str, int]:
    """Count overdue pending items for one tenant without exposing item contents."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    overdue = db.scalar(
        select(func.count(ReviewQueueItem.id)).where(
            ReviewQueueItem.company_id == company_id,
            ReviewQueueItem.status == "pending",
            ReviewQueueItem.created_at < cutoff,
        )
    )
    return {"older_than_hours": older_than_hours, "overdue_pending": int(overdue or 0)}
