"""PostgreSQL-backed internal work. No external action handlers are registered."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InternalTask, ReviewQueueItem
from app.schemas import ReviewQueueTrigger
from app.services.commercial_pipeline import build_review_item

MAX_ATTEMPTS = 3
LEASE_SECONDS = 60


def utcnow():
    return datetime.now(timezone.utc)


def get_task(db: Session, task_id: int, company_id: int):
    return db.scalar(select(InternalTask).where(
        InternalTask.id == task_id, InternalTask.company_id == company_id,
    ))


def list_tasks(db: Session, company_id: int, *, status=None, limit=50, offset=0):
    query = select(InternalTask).where(InternalTask.company_id == company_id)
    if status is not None:
        query = query.where(InternalTask.status == status)
    return db.scalars(query.order_by(InternalTask.created_at.desc(), InternalTask.id.desc())
                      .offset(offset).limit(limit)).all()


def task_summary(db: Session, company_id: int, *, now=None):
    """Single tenant-filtered snapshot. Retry waiting is not overdue work."""
    now = now or utcnow()
    predicates = {state: InternalTask.status == state
                  for state in ("queued", "running", "succeeded", "failed")}
    predicates["overdue_queued"] = (
        (InternalTask.status == "queued") &
        (InternalTask.available_at < now - timedelta(hours=24))
    )
    predicates["expired_running"] = (
        (InternalTask.status == "running") & (InternalTask.lease_until <= now)
    )
    row = db.execute(select(*[
        func.count(case((predicate, 1))).label(name)
        for name, predicate in predicates.items()
    ]).where(InternalTask.company_id == company_id)).one()
    return dict(row._mapping)


def enqueue(db: Session, trigger: ReviewQueueTrigger, company_id: int):
    payload = trigger.model_dump()
    query = select(InternalTask).where(
        InternalTask.company_id == company_id, InternalTask.event_id == trigger.event_id,
    )
    existing = db.scalar(query)
    if existing is None:
        task = InternalTask(company_id=company_id, event_id=trigger.event_id,
                            payload=payload, available_at=utcnow())
        try:
            with db.begin_nested():
                db.add(task)
                db.flush()
        except IntegrityError:
            existing = db.scalar(query)
            if existing is None:
                raise
        else:
            db.commit()
            return task
    if existing.payload != payload:
        raise ValueError("Event already registered with different input")
    return existing


def recover_expired(db: Session, *, now=None, limit=100):
    now = now or utcnow()
    expired = db.execute(select(
        InternalTask.id, InternalTask.claim_token, InternalTask.attempts,
    ).where(InternalTask.status == "running", InternalTask.lease_until <= now)
        .order_by(InternalTask.lease_until, InternalTask.id).limit(limit)).all()
    count = 0
    for task_id, token, attempts in expired:
        result = db.execute(update(InternalTask).execution_options(synchronize_session="fetch").where(
            InternalTask.id == task_id, InternalTask.status == "running",
            InternalTask.claim_token == token, InternalTask.lease_until <= now,
        ).values(status="failed" if attempts >= MAX_ATTEMPTS else "queued",
                 claim_token=None, lease_until=None, error_code="lease_expired",
                 available_at=now + timedelta(seconds=2 ** attempts)))
        count += result.rowcount
    db.commit()
    return count


def claim(db: Session, *, now=None):
    now = now or utcnow()
    ready = (InternalTask.status == "queued", InternalTask.available_at <= now,
             InternalTask.attempts < MAX_ATTEMPTS)
    ids = db.scalars(select(InternalTask.id).where(*ready)
                     .order_by(InternalTask.available_at, InternalTask.id).limit(20)).all()
    for task_id in ids:
        token = str(uuid4())
        result = db.execute(update(InternalTask).execution_options(synchronize_session="fetch").where(InternalTask.id == task_id, *ready)
            .values(status="running", attempts=InternalTask.attempts + 1,
                    claim_token=token, lease_until=now + timedelta(seconds=LEASE_SECONDS)))
        if result.rowcount == 1:
            db.commit()
            return task_id, token
    db.rollback()
    return None


def execute_claim(db: Session, task_id: int, token: str, service_context: str, *, now=None):
    """Fence before any effect; result and completion share one transaction.

    Only short deterministic local triage is allowed while holding this lock.
    Network/LLM handlers must not be added to this transaction.
    """
    now = now or utcnow()
    locked = db.execute(update(InternalTask).execution_options(synchronize_session="fetch").where(
        InternalTask.id == task_id, InternalTask.status == "running",
        InternalTask.claim_token == token, InternalTask.lease_until > now,
    ).values(claim_token=token))
    if locked.rowcount != 1:
        db.rollback()
        return False
    task = db.get(InternalTask, task_id, populate_existing=True)
    trigger = ReviewQueueTrigger.model_validate(task.payload)
    query = select(ReviewQueueItem).where(
        ReviewQueueItem.company_id == task.company_id,
        ReviewQueueItem.event_id == task.event_id,
    )
    item = db.scalar(query)
    if item is None:
        item = build_review_item(trigger, task.company_id, service_context)
        try:
            with db.begin_nested():
                db.add(item)
                db.flush()
        except IntegrityError:
            item = db.scalar(query)
            if item is None:
                raise
    if item.channel != trigger.channel or item.message != trigger.message:
        raise ValueError("Conflicting review input")
    task.status = "succeeded"
    task.result = {"review_item_id": item.id}
    task.claim_token = None
    task.lease_until = None
    task.error_code = None
    db.commit()
    return True


def fail_claim(db: Session, task_id: int, token: str, *, now=None):
    now = now or utcnow()
    task = db.scalar(select(InternalTask).where(
        InternalTask.id == task_id, InternalTask.status == "running",
        InternalTask.claim_token == token,
    ))
    if task is None:
        return False
    attempts = task.attempts
    result = db.execute(update(InternalTask).execution_options(synchronize_session="fetch").where(
        InternalTask.id == task_id, InternalTask.status == "running",
        InternalTask.claim_token == token, InternalTask.lease_until > now,
    ).values(status="failed" if attempts >= MAX_ATTEMPTS else "queued",
             available_at=now + timedelta(seconds=2 ** attempts),
             claim_token=None, lease_until=None, error_code="processing_failed"))
    db.commit()
    return result.rowcount == 1


def run_once(session_factory, service_context: str):
    with session_factory() as db:
        recover_expired(db)
        claimed = claim(db)
        if claimed is None:
            return False
        try:
            execute_claim(db, *claimed, service_context)
        except Exception:
            # Worker boundary: roll back all effects, record a bounded retry.
            # Never expose exception text (it may include payload/SQL values).
            db.rollback()
            fail_claim(db, *claimed)
        return True
