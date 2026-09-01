from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Company, Conversation, Customer, Lead, Message
from app.routers.companies import router as companies_router
from app.routers.customers import router as customers_router
from app.routers.leads import router as leads_router
from app.schemas import (
    AgentRequest,
    ConversationCreate,
    MessageCreate,
)
from app.services.agent import AgentServiceError, generate_agent_reply


app = FastAPI(
    title="Fenato Business Automation API",
    version="0.1.0",
)

app.include_router(companies_router)
app.include_router(customers_router)
app.include_router(leads_router)


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Fenato Business Automation API",
        "status": "running",
    }


@app.post("/conversations/{conversation_id}/agent-reply")
def agent_reply(
    conversation_id: int,
    data: AgentRequest,
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

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


@app.post("/conversations")
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
):
    company = db.get(Company, data.company_id)

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
        lead = db.get(Lead, data.lead_id)

        if lead is None:
            raise HTTPException(
                status_code=404,
                detail="Lead not found",
            )

        if lead.company_id != data.company_id:
            raise HTTPException(
                status_code=400,
                detail="Lead does not belong to this company",
            )

    if data.customer_id is not None:
        customer = db.get(Customer, data.customer_id)

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

        if customer.company_id != data.company_id:
            raise HTTPException(
                status_code=400,
                detail="Customer does not belong to this company",
            )

    conversation = Conversation(
        company_id=data.company_id,
        lead_id=data.lead_id,
        customer_id=data.customer_id,
        channel=data.channel,
        status="open",
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@app.post("/conversations/{conversation_id}/messages")
def create_message(
    conversation_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
):
    conversation = db.get(
        Conversation,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
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


@app.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conversation = db.get(
        Conversation,
        conversation_id,
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
