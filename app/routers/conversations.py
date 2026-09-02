from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import (
    AuthenticatedContext,
    get_authenticated_context,
    get_db,
    require_matching_company,
)
from app.models import Conversation, Customer, Lead, Message
from app.schemas import AgentRequest, ConversationCreate, MessageCreate
from app.services.agent import AgentServiceError, generate_agent_reply


router = APIRouter()


@router.post("/conversations/{conversation_id}/agent-reply")
def agent_reply(
    conversation_id: int,
    data: AgentRequest,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.company_id == context.company.id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    company = context.company

    # Recupera o histórico ANTES da nova mensagem
    history_messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    ).all()

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    # Salva mensagem recebida antes de chamar o Ollama
    customer_message = Message(
        conversation_id=conversation_id,
        sender_type="customer",
        content=data.content,
    )

    db.add(customer_message)
    db.commit()

    # Gera resposta usando Ollama/Qwen
    try:
        response = generate_agent_reply(
            message=data.content,
            history=history,
            instructions=company.agent_instructions,
            model=company.agent_model,
        )
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    # Salva resposta do agente
    agent_message = Message(
        conversation_id=conversation_id,
        sender_type="agent",
        content=response,
    )

    db.add(agent_message)
    db.commit()

    return {
        "conversation_id": conversation_id,
        "reply": response,
    }


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.company_id == context.company.id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


@router.get("/companies/{company_id}/conversations")
def list_company_conversations(
    company_id: int,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    require_matching_company(context, company_id)

    return db.scalars(
        select(Conversation)
        .where(Conversation.company_id == context.company.id)
        .order_by(Conversation.id)
    ).all()


@router.post("/conversations")
def create_conversation(
    data: ConversationCreate,
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    if data.company_id != context.company.id:
        raise HTTPException(
            status_code=400,
            detail="company_id must match the authenticated company",
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
                Lead.company_id == context.company.id,
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
                Customer.company_id == context.company.id,
            )
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

    conversation = Conversation(
        company_id=context.company.id,
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
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.company_id == context.company.id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    if data.sender_type != "human":
        raise HTTPException(
            status_code=403,
            detail="sender_type is not allowed for authenticated users",
        )

    message = Message(
        conversation_id=conversation_id,
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
    context: Annotated[
        AuthenticatedContext,
        Depends(get_authenticated_context),
    ],
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.company_id == context.company.id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    ).all()
