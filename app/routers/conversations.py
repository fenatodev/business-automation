from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import (
    ensure_company_match,
    get_db,
    require_operator,
    require_operator_company,
)
from app.models import Company, Conversation, Customer, Lead, Message
from app.schemas import AgentRequest, ConversationCreate, MessageCreate
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


@router.get("/companies/{company_id}/conversations")
def list_company_conversations(
    company_id: int,
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

    return db.scalars(
        select(Conversation)
        .where(Conversation.company_id == company_id)
        .order_by(Conversation.id)
    ).all()


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
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    return db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id)
    ).all()
