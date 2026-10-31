import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session, joinedload

from app.auth import AccessIdentity
from app.dependencies import (
    ensure_company_match,
    get_db,
    require_operator,
    require_operator_company,
)
from app.models import Company, Conversation, Customer, Lead, Message
from app.schemas import AgentRequest, ConversationBulkStatus, ConversationCreate, ConversationUpdate, MessageCreate
from app.services.agent import AgentServiceError, generate_agent_reply


router = APIRouter()


def _get_tenant_conversation(
    db: Session,
    conversation_id: int,
    company_id: int,
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.company_id == company_id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


@router.post("/conversations/{conversation_id}/agent-reply")
def agent_reply(
    conversation_id: int,
    data: AgentRequest,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    history_messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id)
    ).all()

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    customer_message = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        content=data.content,
    )

    db.add(customer_message)
    db.commit()

    try:
        response = generate_agent_reply(
            message=data.content,
            history=history,
        )
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    agent_message = Message(
        conversation_id=conversation.id,
        sender_type="agent",
        content=response,
    )

    db.add(agent_message)
    db.commit()

    return {
        "conversation_id": conversation.id,
        "reply": response,
    }


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    if data.status is not None:
        conversation.status = data.status

    if data.note is not None:
        note_msg = Message(
            conversation_id=conversation.id,
            sender_type="system",
            content="📝 Nota interna: " + data.note,
        )
        db.add(note_msg)

    db.commit()
    db.refresh(conversation)

    return conversation


@router.get("/conversations/{conversation_id}/note")
def get_conversation_note(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Get the most recent internal note for a conversation."""
    _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    note = db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_type == "system",
            Message.content.like("📝 Nota interna:%"),
        )
        .order_by(desc(Message.id))
        .limit(1)
    )

    if note is None:
        return {"note": None}

    # Strip the prefix to return just the note content
    content = note.content
    if content.startswith("📝 Nota interna: "):
        content = content[len("📝 Nota interna: "):]
    return {"note": content}


@router.get("/companies/{company_id}/conversations")
def list_company_conversations(
    company_id: int,
    channel: str | None = Query(None, description="Filter by channel"),
    status: str | None = Query(None, description="Filter by status"),
    q: str | None = Query(None, description="Search keywords in messages"),
    customer_id: int | None = Query(None, description="Filter by customer"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: str = Query(default="last_message", description="Sort by: id, last_message, created_at"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator_company),
):
    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    stmt = select(Conversation).where(Conversation.company_id == company_id)

    if channel is not None:
        stmt = stmt.where(Conversation.channel == channel)

    if status is not None:
        stmt = stmt.where(Conversation.status == status)

    if customer_id is not None:
        stmt = stmt.where(Conversation.customer_id == customer_id)

    if q is not None:
        stmt = stmt.where(
            Conversation.id.in_(
                select(Message.conversation_id).where(
                    func.lower(Message.content).like(f"%{q.lower()}%")
                )
            )
        )

    # WP-151 — date range filter on created_at (ISO 8601 string comparison)
    if from_date:
        stmt = stmt.where(Conversation.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Conversation.created_at <= to_date + "T23:59:59")

    if sort == "last_message":
        last_msg = (
            select(func.max(Message.created_at))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        stmt = stmt.order_by(desc(last_msg), Conversation.id)
    elif sort == "created_at":
        stmt = stmt.order_by(desc(Conversation.created_at), Conversation.id)
    else:
        stmt = stmt.order_by(Conversation.id)

    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


@router.get("/companies/{company_id}/conversations/count")
def count_company_conversations(
    company_id: int,
    channel: str | None = Query(None, description="Filter by channel"),
    status: str | None = Query(None, description="Filter by status"),
    q: str | None = Query(None, description="Search keywords in messages"),
    customer_id: int | None = Query(None, description="Filter by customer"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator_company),
):
    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    stmt = select(func.count()).select_from(Conversation).where(Conversation.company_id == company_id)

    if channel is not None:
        stmt = stmt.where(Conversation.channel == channel)

    if status is not None:
        stmt = stmt.where(Conversation.status == status)

    if customer_id is not None:
        stmt = stmt.where(Conversation.customer_id == customer_id)

    if q is not None:
        stmt = stmt.where(
            Conversation.id.in_(
                select(Message.conversation_id).where(
                    func.lower(Message.content).like(f"%{q.lower()}%")
                )
            )
        )

    # WP-151 — date range filter
    if from_date:
        stmt = stmt.where(Conversation.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Conversation.created_at <= to_date + "T23:59:59")

    total = db.scalar(stmt)
    return {"total": total}


@router.post("/conversations/bulk-status")
def bulk_update_conversation_status(
    data: ConversationBulkStatus,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk update status for multiple conversations (tenant-isolated)."""
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.id.in_(data.conversation_ids),
            Conversation.company_id == identity.company_id,
        )
    ).all()

    updated = []
    skipped = []

    for conv in conversations:
        conv.status = data.status
        updated.append(conv.id)

    for cid in data.conversation_ids:
        if cid not in updated:
            skipped.append(cid)

    db.commit()

    return {
        "updated": len(updated),
        "updated_ids": updated,
        "skipped": skipped,
    }


@router.post("/conversations")
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    ensure_company_match(identity, data.company_id)

    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    if data.lead_id is None and data.customer_id is None:
        raise HTTPException(
            status_code=400,
            detail="Conversation must belong to a lead or customer",
        )

    if data.lead_id is not None and data.customer_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Conversation cannot belong to both lead and customer",
        )

    if data.lead_id is not None:
        lead = db.scalar(
            select(Lead).where(
                Lead.id == data.lead_id,
                Lead.company_id == identity.company_id,
            )
        )

        if lead is None:
            raise HTTPException(
                status_code=404,
                detail="Lead not found",
            )

    if data.customer_id is not None:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == data.customer_id,
                Customer.company_id == identity.company_id,
            )
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

    conversation = Conversation(
        company_id=identity.company_id,
        lead_id=data.lead_id,
        customer_id=data.customer_id,
        channel=data.channel,
        status="open",
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.post("/conversations/{conversation_id}/messages")
def create_message(
    conversation_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    message = Message(
        conversation_id=conversation.id,
        sender_type=data.sender_type,
        content=data.content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """List messages for a conversation with pagination."""
    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    return db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/conversations/{conversation_id}/messages/count")
def count_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Count messages for a conversation."""
    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    total = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.conversation_id == conversation.id)
    )
    return {"total": total}


@router.get("/companies/{company_id}/conversations/export.csv")
def export_conversations_csv(
    company_id: int,
    channel: str | None = Query(None, description="Filter by channel"),
    status: str | None = Query(None, description="Filter by status"),
    q: str | None = Query(None, description="Search keywords in messages"),
    customer_id: int | None = Query(None, description="Filter by customer"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator_company),
):
    """Export tenant conversations with their messages as CSV, respecting filters."""
    company = db.scalar(
        select(Company).where(Company.id == identity.company_id)
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    stmt = select(Conversation).where(Conversation.company_id == company_id)

    if channel is not None:
        stmt = stmt.where(Conversation.channel == channel)

    if status is not None:
        stmt = stmt.where(Conversation.status == status)

    if customer_id is not None:
        stmt = stmt.where(Conversation.customer_id == customer_id)

    if q is not None:
        stmt = stmt.where(
            Conversation.id.in_(
                select(Message.conversation_id).where(
                    func.lower(Message.content).like(f"%{q.lower()}%")
                )
            )
        )

    # WP-151 — date range filter
    if from_date:
        stmt = stmt.where(Conversation.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Conversation.created_at <= to_date + "T23:59:59")

    conversations = db.scalars(stmt.order_by(Conversation.id)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Canal", "Status", "Lead", "Customer",
        "Mensagens", "Criado em",
    ])

    for conv in conversations:
        messages = db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.id)
        ).all()
        message_text = " | ".join(
            f"[{msg.sender_type}] {msg.content}" for msg in messages
        ) if messages else ""

        writer.writerow([
            conv.id,
            conv.channel,
            conv.status,
            conv.lead_id or "",
            conv.customer_id or "",
            message_text,
            conv.created_at.isoformat() if conv.created_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=conversations.csv",
        },
    )
