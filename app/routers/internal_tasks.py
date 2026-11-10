"""Operator-only creation/status for internal synthetic intake tasks."""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.models import Conversation, InternalTask, Lead, Opportunity, ProposalBrief, ReviewQueueItem
from app.schemas import InternalTaskBulkRetry, InternalTaskOut, ReviewQueueTrigger
from app.services import internal_tasks as tasks
from app.services.internal_tasks import task_count as task_count_svc

router = APIRouter(prefix="/internal-tasks", tags=["internal-tasks"])


@router.get("/", response_model=list[InternalTaskOut])
def list_internal_tasks(
    status: Literal["queued", "running", "succeeded", "failed"] | None = None,
    q: str | None = Query(None, description="Search keywords in event_id, error_code"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: Literal["id", "created_at", "status", "attempts"] = "created_at",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return tasks.list_tasks(db, identity.company_id, status=status, q=q, limit=limit, offset=offset, sort=sort, from_date=from_date, to_date=to_date)


@router.get("/count", response_model=int)
def count_internal_tasks(
    status: Literal["queued", "running", "succeeded", "failed"] | None = None,
    q: str | None = Query(None, description="Search keywords in event_id, error_code"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return task_count_svc(db, identity.company_id, status=status, q=q, from_date=from_date, to_date=to_date)


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
    period: int | None = Query(default=None, ge=1, le=365, description="Filter metrics by last N days (7, 30, 90)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Aggregate dashboard counts for the authenticated tenant.

    WP-517 — Optional period filter: when set, only counts records created
    in the last N days.  Defaults to all-time when omitted.
    """
    company_id = identity.company_id

    cutoff = None
    if period is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=period)

    def _cutoff_filter(model):
        if cutoff is not None:
            return model.created_at >= cutoff
        return True

    # Opportunities by next_action
    opp_query = (
        select(Opportunity.next_action, func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id, _cutoff_filter(Opportunity))
        .group_by(Opportunity.next_action)
    )
    opp_rows = db.execute(opp_query).all()
    opportunities = {"total": sum(c for _, c in opp_rows)}
    for action, count in opp_rows:
        opportunities[action] = int(count)

    # Conversations by status
    conv_query = (
        select(Conversation.status, func.count(Conversation.id))
        .where(Conversation.company_id == company_id, _cutoff_filter(Conversation))
        .group_by(Conversation.status)
    )
    conv_rows = db.execute(conv_query).all()
    conversations = {"total": sum(c for _, c in conv_rows)}
    for status, count in conv_rows:
        conversations[status] = int(count)

    # Leads by status
    lead_query = (
        select(Lead.status, func.count(Lead.id))
        .where(Lead.company_id == company_id, _cutoff_filter(Lead))
        .group_by(Lead.status)
    )
    lead_rows = db.execute(lead_query).all()
    leads = {"total": sum(c for _, c in lead_rows)}
    for status, count in lead_rows:
        leads[status] = int(count)

    # Internal tasks summary
    task_summary = tasks.task_summary(db, company_id)

    # Review queue summary
    rq_query = (
        select(ReviewQueueItem.status, func.count(ReviewQueueItem.id))
        .where(ReviewQueueItem.company_id == company_id, _cutoff_filter(ReviewQueueItem))
        .group_by(ReviewQueueItem.status)
    )
    rq_rows = db.execute(rq_query).all()
    review_queue = {"total": sum(c for _, c in rq_rows)}
    for status, count in rq_rows:
        review_queue[status] = int(count)

    # WP-244 — Briefs by status (tenant-isolated via JOIN with Opportunity)
    brief_query = (
        select(ProposalBrief.status, func.count(ProposalBrief.id))
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == company_id, _cutoff_filter(ProposalBrief))
        .group_by(ProposalBrief.status)
    )
    brief_rows = db.execute(brief_query).all()
    briefs = {"total": sum(c for _, c in brief_rows)}
    for status, count in brief_rows:
        briefs[status] = int(count)

    # WP-198 — Opportunities by source
    opp_source_query = (
        select(Opportunity.source, func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id, _cutoff_filter(Opportunity))
        .group_by(Opportunity.source)
    )
    opp_source_rows = db.execute(opp_source_query).all()
    opportunities_by_source = {"total": sum(c for _, c in opp_source_rows)}
    for source, count in opp_source_rows:
        opportunities_by_source[source] = int(count)

    # WP-199 — Leads by source
    lead_source_query = (
        select(Lead.source, func.count(Lead.id))
        .where(Lead.company_id == company_id, _cutoff_filter(Lead))
        .group_by(Lead.source)
    )
    lead_source_rows = db.execute(lead_source_query).all()
    leads_by_source = {"total": sum(c for _, c in lead_source_rows)}
    for source, count in lead_source_rows:
        leads_by_source[source] = int(count)

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
    # WP-245 — Briefs ready for review
    if briefs.get("ready_for_review", 0) > 0:
        next_actions.append({
            "type": "brief",
            "label": f"{briefs['ready_for_review']} brief(s) pronto(s) para revisão",
            "count": briefs["ready_for_review"],
            "section": "briefs",
        })

    # WP-216 — Agent usage stats
    from app.routers.companies import _get_agent_usage
    agent_usage = _get_agent_usage(company_id)

    # WP-239 — High priority opportunities (reuse _calculate_priority_score from opportunities)
    from app.routers.opportunities import _calculate_priority_score
    all_opps = db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == company_id, _cutoff_filter(Opportunity))
        .order_by(Opportunity.id)
    ).all()
    high_priority = []
    for opp in all_opps:
        priority = _calculate_priority_score(opp)
        if priority["level"] == "high":
            high_priority.append({
                "id": opp.id,
                "title": opp.title,
                "priority_score": priority["score"],
                "priority_level": priority["level"],
                "next_action": opp.next_action,
                "deadline": opp.deadline,
                "budget": opp.budget,
                "source": opp.source,
            })
    high_priority.sort(key=lambda x: x["priority_score"], reverse=True)
    high_priority_opportunities = high_priority[:5]

    # WP-228 — Recent activities (inline with dashboard to avoid separate fetch)
    activities = []
    for opp in db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == company_id, _cutoff_filter(Opportunity))
        .order_by(Opportunity.created_at.desc())
        .limit(10)
    ).all():
        activities.append({
            "type": "opportunity",
            "id": opp.id,
            "title": opp.title,
            "created_at": opp.created_at.isoformat(),
        })
    for conv in db.scalars(
        select(Conversation)
        .where(Conversation.company_id == company_id, _cutoff_filter(Conversation))
        .order_by(Conversation.created_at.desc())
        .limit(10)
    ).all():
        activities.append({
            "type": "conversation",
            "id": conv.id,
            "title": f"Conversa ({conv.channel})",
            "created_at": conv.created_at.isoformat(),
        })
    for lead in db.scalars(
        select(Lead)
        .where(Lead.company_id == company_id, _cutoff_filter(Lead))
        .order_by(Lead.created_at.desc())
        .limit(10)
    ).all():
        activities.append({
            "type": "lead",
            "id": lead.id,
            "title": lead.name,
            "created_at": lead.created_at.isoformat(),
        })
    activities.sort(key=lambda a: a["created_at"], reverse=True)
    recent_activities = activities[:20]

    # WP-256 — Business performance metrics
    # Lead conversion rate: leads converted to customers / total leads
    total_leads = db.scalar(
        select(func.count(Lead.id)).where(Lead.company_id == company_id, _cutoff_filter(Lead))
    ) or 0
    converted_leads = db.scalar(
        select(func.count(Lead.id)).where(
            Lead.company_id == company_id,
            Lead.status == "converted",
            _cutoff_filter(Lead),
        )
    ) or 0
    lead_conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0.0

    # Opportunity closure rate: done + lost / total opportunities
    total_opps = db.scalar(
        select(func.count(Opportunity.id)).where(Opportunity.company_id == company_id, _cutoff_filter(Opportunity))
    ) or 0
    closed_opps = db.scalar(
        select(func.count(Opportunity.id)).where(
            Opportunity.company_id == company_id,
            Opportunity.next_action.in_(["done", "lost", "ignore"]),
            _cutoff_filter(Opportunity),
        )
    ) or 0
    opportunity_closure_rate = (closed_opps / total_opps * 100) if total_opps > 0 else 0.0

    # Brief approval rate: approved / total briefs
    total_briefs = db.scalar(
        select(func.count(ProposalBrief.id))
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == company_id, _cutoff_filter(ProposalBrief))
    ) or 0
    approved_briefs = db.scalar(
        select(func.count(ProposalBrief.id))
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            Opportunity.company_id == company_id,
            ProposalBrief.status == "approved",
            _cutoff_filter(ProposalBrief),
        )
    ) or 0
    brief_approval_rate = (approved_briefs / total_briefs * 100) if total_briefs > 0 else 0.0

    performance_metrics = {
        "lead_conversion_rate": round(lead_conversion_rate, 1),
        "lead_conversion_count": f"{converted_leads}/{total_leads}",
        "opportunity_closure_rate": round(opportunity_closure_rate, 1),
        "opportunity_closure_count": f"{closed_opps}/{total_opps}",
        "brief_approval_rate": round(brief_approval_rate, 1),
        "brief_approval_count": f"{approved_briefs}/{total_briefs}",
    }

    return {
        "period": period,
        "opportunities": opportunities,
        "conversations": conversations,
        "leads": leads,
        "tasks": task_summary,
        "review_queue": review_queue,
        "opportunities_by_source": opportunities_by_source,
        "leads_by_source": leads_by_source,
        "next_actions": next_actions,
        "agent_usage": {
            "total_calls": agent_usage["total_calls"],
            "successful_calls": agent_usage["successful_calls"],
            "failed_calls": agent_usage["failed_calls"],
        },
        "briefs": briefs,
        "high_priority_opportunities": high_priority_opportunities,
        "recent_activities": recent_activities,
        "performance_metrics": performance_metrics,
    }


@router.get("/notification-summary", response_model=dict[str, dict[str, int]])
def get_notification_summary(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Return only the tenant-scoped counters needed by the operator bell."""
    company_id = identity.company_id
    opportunities_pending = db.scalar(
        select(func.count(Opportunity.id)).where(
            Opportunity.company_id == company_id,
            Opportunity.next_action == "pending",
        )
    ) or 0
    conversations_open = db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.company_id == company_id,
            Conversation.status == "open",
        )
    ) or 0
    leads_new = db.scalar(
        select(func.count(Lead.id)).where(
            Lead.company_id == company_id,
            Lead.status == "new",
        )
    ) or 0
    task_summary = tasks.task_summary(db, company_id)
    return {
        "opportunities": {"pending": int(opportunities_pending)},
        "conversations": {"open": int(conversations_open)},
        "leads": {"new": int(leads_new)},
        "tasks": {"failed": int(task_summary["failed"])},
    }


@router.get("/export-dashboard.csv")
def export_dashboard_csv(
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-275 — Export a consolidated dashboard report as CSV.

    Combines all dashboard metrics into a single CSV for management reporting.
    """
    company_id = identity.company_id

    # Reuse dashboard logic to gather all metrics
    opp_rows = db.execute(
        select(Opportunity.next_action, func.count(Opportunity.id))
        .where(Opportunity.company_id == company_id)
        .group_by(Opportunity.next_action)
    ).all()
    opportunities = {"total": sum(c for _, c in opp_rows)}
    for action, count in opp_rows:
        opportunities[action] = int(count)

    conv_rows = db.execute(
        select(Conversation.status, func.count(Conversation.id))
        .where(Conversation.company_id == company_id)
        .group_by(Conversation.status)
    ).all()
    conversations = {"total": sum(c for _, c in conv_rows)}
    for status, count in conv_rows:
        conversations[status] = int(count)

    lead_rows = db.execute(
        select(Lead.status, func.count(Lead.id))
        .where(Lead.company_id == company_id)
        .group_by(Lead.status)
    ).all()
    leads = {"total": sum(c for _, c in lead_rows)}
    for status, count in lead_rows:
        leads[status] = int(count)

    task_summary = tasks.task_summary(db, company_id)

    rq_rows = db.execute(
        select(ReviewQueueItem.status, func.count(ReviewQueueItem.id))
        .where(ReviewQueueItem.company_id == company_id)
        .group_by(ReviewQueueItem.status)
    ).all()
    review_queue = {"total": sum(c for _, c in rq_rows)}
    for status, count in rq_rows:
        review_queue[status] = int(count)

    brief_rows = db.execute(
        select(ProposalBrief.status, func.count(ProposalBrief.id))
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == company_id)
        .group_by(ProposalBrief.status)
    ).all()
    briefs = {"total": sum(c for _, c in brief_rows)}
    for status, count in brief_rows:
        briefs[status] = int(count)

    # Agent usage
    from app.routers.companies import _get_agent_usage
    agent_usage = _get_agent_usage(company_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Section 1: Opportunities
    writer.writerow(["OPORTUNIDADES"])
    writer.writerow(["Status", "Quantidade"])
    for key, value in opportunities.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Section 2: Conversations
    writer.writerow(["CONVERSAS"])
    writer.writerow(["Status", "Quantidade"])
    for key, value in conversations.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Section 3: Leads
    writer.writerow(["LEADS"])
    writer.writerow(["Status", "Quantidade"])
    for key, value in leads.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Section 4: Briefs
    writer.writerow(["BRIEFS"])
    writer.writerow(["Status", "Quantidade"])
    for key, value in briefs.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Section 5: Internal Tasks
    writer.writerow(["TAREFAS INTERNAS"])
    writer.writerow(["Status", "Quantidade"])
    for key, value in task_summary.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Section 6: Review Queue
    writer.writerow(["FILA DE REVISAO"])
    writer.writerow(["Status", "Quantidade"])
    for key, value in review_queue.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Section 7: Agent Usage
    writer.writerow(["AGENTE IA"])
    writer.writerow(["Metrica", "Valor"])
    writer.writerow(["Total de chamadas", agent_usage["total_calls"]])
    writer.writerow(["Chamadas bem-sucedidas", agent_usage["successful_calls"]])
    writer.writerow(["Chamadas falhadas", agent_usage["failed_calls"]])
    writer.writerow([])

    # Section 8: Performance Metrics
    total_leads = db.scalar(
        select(func.count(Lead.id)).where(Lead.company_id == company_id)
    ) or 0
    converted_leads = db.scalar(
        select(func.count(Lead.id)).where(
            Lead.company_id == company_id,
            Lead.status == "converted",
        )
    ) or 0
    lead_conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0.0

    total_opps = db.scalar(
        select(func.count(Opportunity.id)).where(Opportunity.company_id == company_id)
    ) or 0
    closed_opps = db.scalar(
        select(func.count(Opportunity.id)).where(
            Opportunity.company_id == company_id,
            Opportunity.next_action.in_(["done", "lost", "ignore"]),
        )
    ) or 0
    opportunity_closure_rate = (closed_opps / total_opps * 100) if total_opps > 0 else 0.0

    total_briefs = db.scalar(
        select(func.count(ProposalBrief.id))
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(Opportunity.company_id == company_id)
    ) or 0
    approved_briefs = db.scalar(
        select(func.count(ProposalBrief.id))
        .join(Opportunity, ProposalBrief.opportunity_id == Opportunity.id)
        .where(
            Opportunity.company_id == company_id,
            ProposalBrief.status == "approved",
        )
    ) or 0
    brief_approval_rate = (approved_briefs / total_briefs * 100) if total_briefs > 0 else 0.0

    writer.writerow(["INDICADORES DE PERFORMANCE"])
    writer.writerow(["Indicador", "Taxa (%)", "Contagem"])
    writer.writerow(["Taxa de conversao de leads", round(lead_conversion_rate, 1), f"{converted_leads}/{total_leads}"])
    writer.writerow(["Taxa de fechamento de oportunidades", round(opportunity_closure_rate, 1), f"{closed_opps}/{total_opps}"])
    writer.writerow(["Taxa de aprovacao de briefs", round(brief_approval_rate, 1), f"{approved_briefs}/{total_briefs}"])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=dashboard_report.csv",
        },
    )


@router.get("/recent-activities")
def get_recent_activities(
    limit: int = Query(default=20, ge=1, le=100),
    type: str | None = Query(None, alias="type", description="Filter by activity type"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-223 — Return recent activities across all entities.

    Gives the operator quick context on what's happening in their tenant.
    """
    company_id = identity.company_id
    activities = []

    # Opportunities
    opps = db.scalars(
        select(Opportunity)
        .where(Opportunity.company_id == company_id)
        .order_by(Opportunity.created_at.desc())
        .limit(limit)
    ).all()
    for opp in opps:
        activities.append({
            "type": "opportunity",
            "id": opp.id,
            "title": opp.title,
            "created_at": opp.created_at.isoformat(),
        })

    # Conversations
    convs = db.scalars(
        select(Conversation)
        .where(Conversation.company_id == company_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    ).all()
    for conv in convs:
        activities.append({
            "type": "conversation",
            "id": conv.id,
            "title": f"Conversa ({conv.channel})",
            "created_at": conv.created_at.isoformat(),
        })

    # Leads
    leads = db.scalars(
        select(Lead)
        .where(Lead.company_id == company_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    ).all()
    for lead in leads:
        activities.append({
            "type": "lead",
            "id": lead.id,
            "title": lead.name,
            "created_at": lead.created_at.isoformat(),
        })

    # Sort all activities by created_at descending
    activities.sort(key=lambda a: a["created_at"], reverse=True)

    # Filter by type if requested
    if type:
        activities = [a for a in activities if a["type"] == type]

    # Apply limit after sorting
    activities = activities[:limit]

    return {"activities": activities}


@router.get("/export.csv")
def export_tasks_csv(
    sort: Literal["id", "created_at", "status", "attempts"] | None = None,
    status: Literal["queued", "running", "succeeded", "failed"] | None = Query(None, description="Filter by status"),
    q: str | None = Query(None, description="Search keywords in event_id, error_code"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Export tenant internal tasks as a CSV file, respecting filters."""
    query = select(InternalTask).where(InternalTask.company_id == identity.company_id)
    if status:
        query = query.where(InternalTask.status == status)
    # WP-225 — keyword search
    if q:
        lower_q = func.lower(f"%{q}%")
        query = query.where(
            (func.lower(InternalTask.event_id).like(lower_q)) |
            (func.lower(InternalTask.error_code).like(lower_q))
        )
    # WP-155 — date range filter
    if from_date:
        query = query.where(InternalTask.created_at >= from_date)
    if to_date:
        query = query.where(InternalTask.created_at <= to_date + "T23:59:59")
    if sort is None:
        query = query.order_by(InternalTask.id)
    else:
        sort_column = {
            "id": InternalTask.id,
            "created_at": InternalTask.created_at,
            "status": InternalTask.status,
            "attempts": InternalTask.attempts,
        }[sort]
        query = query.order_by(sort_column.desc(), InternalTask.id.desc())
    task_list = db.scalars(query).all()

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


# ---------------------------------------------------------------------------
# WP-545 — Follow-up task creation
# ---------------------------------------------------------------------------


@router.post("/followup", response_model=InternalTaskOut)
def create_followup_task(
    data: dict,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Create a follow-up task for a stale opportunity."""
    opportunity_id = data.get("opportunity_id")
    if not opportunity_id:
        raise HTTPException(status_code=400, detail="opportunity_id required")

    opp = db.scalar(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.company_id == identity.company_id,
        )
    )
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    import uuid

    from app.schemas import ReviewQueueTrigger

    trigger = ReviewQueueTrigger(
        channel="internal",
        message=f"Follow-up: {opp.title or f'Opportunity #{opp.id}'}",
        event_id=str(uuid.uuid4()),
    )
    task = tasks.enqueue(db, trigger, identity.company_id)
    return InternalTaskOut.model_validate(task)
