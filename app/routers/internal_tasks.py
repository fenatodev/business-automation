"""Operator-only creation/status for internal synthetic intake tasks."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Conversation, Lead, Opportunity, ReviewQueueItem
from app.schemas import InternalTaskOut, ReviewQueueTrigger
from app.services import internal_tasks as tasks

router = APIRouter(prefix="/internal-tasks", tags=["internal-tasks"])


@router.get("/", response_model=list[InternalTaskOut])
def list_internal_tasks(
    status: Literal["queued", "running", "succeeded", "failed"] | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return tasks.list_tasks(db, identity.company_id, status=status, limit=limit, offset=offset)


@router.get("/summary", response_model=dict[str, int])
def summarize_internal_tasks(db: Session = Depends(get_db),
                             identity: AccessIdentity = Depends(require_operator)):
    return tasks.task_summary(db, identity.company_id)


@router.post("/", response_model=InternalTaskOut, status_code=202)
def create_task(trigger: ReviewQueueTrigger, db: Session = Depends(get_db),
                identity: AccessIdentity = Depends(require_operator)):
    try:
        return tasks.enqueue(db, trigger, identity.company_id)
    except ValueError:
        raise HTTPException(409, "Event already registered with different input")


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Aggregate dashboard counts for the authenticated tenant."""
    company_id = identity.company_id

    # Opportunities by next_action
    opp_rows = db.execute(
        select(Opportunity.next_action, func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
        .group_by(Opportunity.next_action)
    ).all()
    opportunities = {"total": sum(c for _, c in opp_rows)}
    for action, count in opp_rows:
        opportunities[action] = int(count)

    # Conversations by status
    conv_rows = db.execute(
        select(Conversation.status, func.count(Conversation.id))
        .where(Conversation.company_id == company_id)
        .group_by(Conversation.status)
    ).all()
    conversations = {"total": sum(c for _, c in conv_rows)}
    for status, count in conv_rows:
        conversations[status] = int(count)

    # Leads by status
    lead_rows = db.execute(
        select(Lead.status, func.count(Lead.id))
        .where(Lead.company_id == company_id)
        .group_by(Lead.status)
    ).all()
    leads = {"total": sum(c for _, c in lead_rows)}
    for status, count in lead_rows:
        leads[status] = int(count)

    # Internal tasks summary
    task_summary = tasks.task_summary(db, company_id)

    # Review queue summary
    rq_rows = db.execute(
        select(ReviewQueueItem.status, func.count(ReviewQueueItem.id))
        .where(ReviewQueueItem.company_id == company_id)
        .group_by(ReviewQueueItem.status)
    ).all()
    review_queue = {"total": sum(c for _, c in rq_rows)}
    for status, count in rq_rows:
        review_queue[status] = int(count)

    return {
        "opportunities": opportunities,
        "conversations": conversations,
        "leads": leads,
        "tasks": task_summary,
        "review_queue": review_queue,
    }


@router.get("/{task_id}", response_model=InternalTaskOut)
def task_status(task_id: int, db: Session = Depends(get_db),
                identity: AccessIdentity = Depends(require_operator)):
    task = tasks.get_task(db, task_id, identity.company_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task
