"""Operator-only creation/status for internal synthetic intake tasks."""
import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Conversation, InternalTask, Lead, Opportunity, ReviewQueueItem
from app.schemas import InternalTaskBulkRetry, InternalTaskOut, ReviewQueueTrigger
from app.services import internal_tasks as tasks
from app.services.internal_tasks import task_count as task_count_svc

router = APIRouter(prefix="/internal-tasks", tags=["internal-tasks"])


@router.get("/", response_model=list[InternalTaskOut])
def list_internal_tasks(
    status: Literal["queued", "running", "succeeded", "failed"] | None = None,
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: Literal["id", "created_at", "status", "attempts"] = "created_at",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return tasks.list_tasks(db, identity.company_id, status=status, limit=limit, offset=offset, sort=sort, from_date=from_date, to_date=to_date)


@router.get("/count", response_model=int)
def count_internal_tasks(
    status: Literal["queued", "running", "succeeded", "failed"] | None = None,
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return task_count_svc(db, identity.company_id, status=status, from_date=from_date, to_date=to_date)


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

    # WP-198 — Opportunities by source
    source_rows = db.execute(
        select(Opportunity.source, func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
        .group_by(Opportunity.source)
    ).all()
    opportunities_by_source = {"total": sum(c for _, c in source_rows)}
    for source, count in source_rows:
        opportunities_by_source[source] = int(count)

    # WP-161 — Next actions: items needing immediate attention
    next_actions = []
    if opportunities.get("pending", 0) > 0:
        next_actions.append({
            "type": "opportunity",
            "label": f"{opportunities['pending']} oportunidade(s) pendente(s) de triagem",
            "count": opportunities["pending"],
            "section": "opportunities",
        })
    if conversations.get("open", 0) > 0:
        next_actions.append({
            "type": "conversation",
            "label": f"{conversations['open']} conversa(s) aberta(s)",
            "count": conversations["open"],
            "section": "conversations",
        })
    if leads.get("new", 0) > 0:
        next_actions.append({
            "type": "lead",
            "label": f"{leads['new']} lead(s) novo(s)",
            "count": leads["new"],
            "section": "leads",
        })
    if task_summary.get("failed", 0) > 0:
        next_actions.append({
            "type": "task",
            "label": f"{task_summary['failed']} tarefa(s) falhada(s)",
            "count": task_summary["failed"],
            "section": "tasks",
        })
    if review_queue.get("pending", 0) > 0:
        next_actions.append({
            "type": "review",
            "label": f"{review_queue['pending']} item(ns) na fila de revisão",
            "count": review_queue["pending"],
            "section": "review_queue",
        })

    return {
        "opportunities": opportunities,
        "conversations": conversations,
        "leads": leads,
        "tasks": task_summary,
        "review_queue": review_queue,
        "opportunities_by_source": opportunities_by_source,
        "next_actions": next_actions,
    }


@router.get("/export.csv")
def export_tasks_csv(
    status: Literal["queued", "running", "succeeded", "failed"] | None = Query(None, description="Filter by status"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export tenant internal tasks as a CSV file, respecting filters."""
    query = select(InternalTask).where(InternalTask.company_id == identity.company_id)
    if status:
        query = query.where(InternalTask.status == status)
    # WP-155 — date range filter
    if from_date:
        query = query.where(InternalTask.created_at >= from_date)
    if to_date:
        query = query.where(InternalTask.created_at <= to_date + "T23:59:59")
    task_list = db.scalars(query.order_by(InternalTask.id)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Evento", "Status", "Tentativas", "Erro",
        "Disponível em", "Criada em",
    ])
    for task in task_list:
        writer.writerow([
            task.id,
            task.event_id,
            task.status,
            task.attempts,
            task.error_code or "",
            task.available_at.isoformat() if task.available_at else "",
            task.created_at.isoformat() if task.created_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=internal-tasks.csv",
        },
    )


@router.get("/{task_id}", response_model=InternalTaskOut)
def task_status(task_id: int, db: Session = Depends(get_db),
                identity: AccessIdentity = Depends(require_operator)):
    task = tasks.get_task(db, task_id, identity.company_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@router.post("/{task_id}/retry", response_model=InternalTaskOut)
def retry_task(task_id: int, db: Session = Depends(get_db),
               identity: AccessIdentity = Depends(require_operator)):
    try:
        task = tasks.manual_retry(db, task_id, identity.company_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if task is None:
        raise HTTPException(404, "Task not found")
    return task


@router.post("/retention", response_model=dict[str, int])
def run_retention(
    older_than_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    deleted = tasks.purge_old_tasks(db, identity.company_id, older_than_days=older_than_days)
    return {"deleted": deleted}


@router.post("/bulk-retry")
def bulk_retry_tasks(
    bulk_data: InternalTaskBulkRetry,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
) -> dict[str, object]:
    """Bulk retry multiple failed internal tasks.

    Tenant-isolated. Returns counts of retried and skipped tasks.
    Tasks that cannot be retried are skipped.
    """
    retried = 0
    retried_ids = []
    skipped = []

    for task_id in bulk_data.task_ids:
        try:
            task = tasks.manual_retry(db, task_id, identity.company_id)
            if task is not None:
                retried += 1
                retried_ids.append(task.id)
            else:
                skipped.append(task_id)
        except ValueError:
            skipped.append(task_id)

    return {
        "retried": retried,
        "retried_ids": sorted(retried_ids),
        "skipped": sorted(skipped),
    }
