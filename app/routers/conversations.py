import csv
import io
from typing import Literal

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
from app.models import Company, Conversation, Customer, Lead, Message, Opportunity
from app.schemas import (
    AgentRequest,
    ConversationBulkDelete,
    ConversationBulkStatus,
    ConversationCreate,
    ConversationSummary,
    ConversationUpdate,
    FavoriteResponse,
    FavoriteToggle,
    MessageCreate,
    TriageSuggestion,
)
from app.routers.companies import _favorites_store
from app.services.agent import (
    AgentServiceError,
    generate_agent_reply,
    suggest_triage as _suggest_triage,
)
from app.services.agent import summarize_conversation as _summarize_conversation


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
        # WP-204 — Use company agent config as defaults
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_prompt = data.system_prompt or company_config.get("system_prompt")
        effective_temp = data.temperature if data.temperature is not None else company_config.get("temperature")
        effective_max_tokens = data.max_tokens if data.max_tokens is not None else company_config.get("max_tokens")
        effective_model = data.model if data.model is not None else company_config.get("model")

        response = generate_agent_reply(
            message=data.content,
            history=history,
            system_prompt=effective_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        # WP-216 — Track successful agent call
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        # WP-216 — Track failed agent call
        _record_agent_call(identity.company_id, success=False)
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


@router.post("/conversations/{conversation_id}/agent-reply-async")
def agent_reply_async(
    conversation_id: int,
    data: AgentRequest,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-533 — Async agent reply: create job and return immediately.

    The job generates the reply in the background. Client polls job status
    to get the result.
    """
    from app.services.job_queue import job_queue

    conversation = _get_tenant_conversation(
        db,
        conversation_id,
        identity.company_id,
    )

    # Persist customer message first
    customer_message = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        content=data.content,
    )
    db.add(customer_message)
    db.commit()

    # Build history for the job
    history_messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id)
    ).all()
    history = [
        {"sender_type": item.sender_type, "content": item.content}
        for item in history_messages
    ]

    # Load company agent config
    from app.routers.companies import _agent_config_store

    company_config = _agent_config_store.get(identity.company_id, {})
    effective_prompt = data.system_prompt or company_config.get("system_prompt")
    effective_temp = data.temperature if data.temperature is not None else company_config.get("temperature")
    effective_max_tokens = data.max_tokens if data.max_tokens is not None else company_config.get("max_tokens")
    effective_model = data.model if data.model is not None else company_config.get("model")

    # Create async job
    job = job_queue.create_job(
        task_type="agent_reply",
        company_id=identity.company_id,
        payload={
            "conversation_id": conversation.id,
            "message": data.content,
            "history": history,
            "system_prompt": effective_prompt,
            "temperature": effective_temp,
            "max_tokens": effective_max_tokens,
            "model": effective_model,
            "_company_id": identity.company_id,
        },
    )

    def _run_reply(payload):
        from app.services.agent import generate_agent_reply
        from app.routers.companies import _record_agent_call

        reply = generate_agent_reply(
            message=payload["message"],
            history=payload["history"],
            system_prompt=payload.get("system_prompt"),
            temperature=payload.get("temperature"),
            max_tokens=payload.get("max_tokens"),
            model=payload.get("model"),
        )
        _record_agent_call(payload.get("_company_id"), success=True)
        return reply

    job_queue.execute_job(job.job_id, _run_reply, _async=True)

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "conversation_id": conversation.id,
    }


@router.post("/conversations/{conversation_id}/suggest-reply")
def suggest_reply(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-226 — Suggest an agent reply based on conversation history.

    Uses the last customer message as the trigger. Returns the suggestion
    without persisting it. Uses company agent config as defaults.
    """
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

    # Find the last customer message
    last_customer = None
    for msg in reversed(history_messages):
        if msg.sender_type == "customer":
            last_customer = msg
            break

    if last_customer is None:
        raise HTTPException(
            status_code=400,
            detail="No customer message found in this conversation",
        )

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_prompt = company_config.get("system_prompt")
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=last_customer.content,
            history=history,
            system_prompt=effective_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    return {
        "conversation_id": conversation.id,
        "suggestion": response,
    }


@router.post("/conversations/{conversation_id}/summarize")
def summarize_conversation_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-516 — Generate an AI summary of a conversation.

    Returns a summary with key points and action items. If the agent
    service is unavailable, returns a fallback summary based on the
    last message instead of raising 503.
    """
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

    if not history_messages:
        return ConversationSummary(
            summary="Nenhuma mensagem nesta conversa.",
            key_points=[],
            action_items=[],
        )

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_model = company_config.get("model")

        result = _summarize_conversation(
            history=history,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        # Graceful fallback: return a simple summary from the last message
        from app.routers.companies import _record_agent_call

        _record_agent_call(identity.company_id, success=False)

        last_msg = history_messages[-1]
        summary_text = last_msg.content[:200]
        if len(last_msg.content) > 200:
            summary_text += "..."

        return ConversationSummary(
            summary=f"Última mensagem: {summary_text}",
            key_points=[],
            action_items=[],
        )

    return ConversationSummary(
        summary=result.get("summary", ""),
        key_points=result.get("key_points", []),
        action_items=result.get("action_items", []),
    )


@router.post("/conversations/{conversation_id}/suggest-lead")
def suggest_lead(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-267 — Suggest lead fields from conversation context.

    Analyzes the conversation messages and suggests name, phone and interest
    for creating a lead. Does NOT persist — returns only the suggestion.
    """
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

    if not history_messages:
        raise HTTPException(
            status_code=400,
            detail="No messages found in this conversation",
        )

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    # Build prompt from conversation context
    prompt_parts = []
    for msg in history:
        role = "Cliente" if msg["sender_type"] == "customer" else ("Humano" if msg["sender_type"] == "human" else "Sistema")
        prompt_parts.append(f"{role}: {msg['content']}")
    conversation_text = "\n".join(prompt_parts)

    system_prompt = (
        "Analise esta conversa e extraia informações para criar um lead.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"suggested_name": "nome extraído ou null", '
        '"suggested_phone": "telefone extraído ou null", '
        '"suggested_interest": "interesse/resumo ou null", '
        '"reasoning": "por que extraiu estes dados"}\n'
        "Se não encontrar um campo, use null."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=conversation_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    # Try to parse JSON from response
    import json
    try:
        parsed = json.loads(response)
        return {
            "conversation_id": conversation.id,
            "suggested_name": parsed.get("suggested_name"),
            "suggested_phone": parsed.get("suggested_phone"),
            "suggested_interest": parsed.get("suggested_interest"),
            "reasoning": parsed.get("reasoning", response),
        }
    except (json.JSONDecodeError, AttributeError):
        # Fallback: return raw response as reasoning
        return {
            "conversation_id": conversation.id,
            "suggested_name": None,
            "suggested_phone": None,
            "suggested_interest": None,
            "reasoning": response,
        }


@router.post("/conversations/{conversation_id}/suggest-customer")
def suggest_customer(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-268 — Suggest customer fields from conversation context.

    Analyzes the conversation messages and suggests name, phone and email
    for creating a customer. Does NOT persist — returns only the suggestion.
    """
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

    if not history_messages:
        raise HTTPException(
            status_code=400,
            detail="No messages found in this conversation",
        )

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    # Build prompt from conversation context
    prompt_parts = []
    for msg in history:
        role = "Cliente" if msg["sender_type"] == "customer" else ("Humano" if msg["sender_type"] == "human" else "Sistema")
        prompt_parts.append(f"{role}: {msg['content']}")
    conversation_text = "\n".join(prompt_parts)

    system_prompt = (
        "Analise esta conversa e extraia informações para criar um customer.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"suggested_name": "nome extraído ou null", '
        '"suggested_phone": "telefone extraído ou null", '
        '"suggested_email": "e-mail extraído ou null", '
        '"reasoning": "por que extraiu estes dados"}\n'
        "Se não encontrar um campo, use null."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=conversation_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    # Try to parse JSON from response
    import json
    try:
        parsed = json.loads(response)
        return {
            "conversation_id": conversation.id,
            "suggested_name": parsed.get("suggested_name"),
            "suggested_phone": parsed.get("suggested_phone"),
            "suggested_email": parsed.get("suggested_email"),
            "reasoning": parsed.get("reasoning", response),
        }
    except (json.JSONDecodeError, AttributeError):
        # Fallback: return raw response as reasoning
        return {
            "conversation_id": conversation.id,
            "suggested_name": None,
            "suggested_phone": None,
            "suggested_email": None,
            "reasoning": response,
        }


@router.post("/conversations/{conversation_id}/suggest-opportunity")
def suggest_opportunity(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-269 — Suggest opportunity fields from conversation context.

    Analyzes the conversation messages and suggests title, description,
    budget, deadline and requirements for creating an opportunity.
    Does NOT persist — returns only the suggestion.
    """
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

    if not history_messages:
        raise HTTPException(
            status_code=400,
            detail="No messages found in this conversation",
        )

    history = [
        {
            "sender_type": item.sender_type,
            "content": item.content,
        }
        for item in history_messages
    ]

    prompt_parts = []
    for msg in history:
        role = "Cliente" if msg["sender_type"] == "customer" else ("Humano" if msg["sender_type"] == "human" else "Sistema")
        prompt_parts.append(f"{role}: {msg['content']}")
    conversation_text = "\n".join(prompt_parts)

    system_prompt = (
        "Analise esta conversa e extraia informações para criar uma oportunidade comercial.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"suggested_title": "título curto ou null", '
        '"suggested_description": "descrição ou null", '
        '"suggested_budget": "orçamento ou null", '
        '"suggested_deadline": "prazo ou null", '
        '"suggested_requirements": "requisitos ou null", '
        '"reasoning": "por que extraiu estes dados"}\n'
        "Se não encontrar um campo, use null."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=conversation_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    import json
    try:
        parsed = json.loads(response)
        return {
            "conversation_id": conversation.id,
            "suggested_title": parsed.get("suggested_title"),
            "suggested_description": parsed.get("suggested_description"),
            "suggested_budget": parsed.get("suggested_budget"),
            "suggested_deadline": parsed.get("suggested_deadline"),
            "suggested_requirements": parsed.get("suggested_requirements"),
            "reasoning": parsed.get("reasoning", response),
        }
    except (json.JSONDecodeError, AttributeError):
        return {
            "conversation_id": conversation.id,
            "suggested_title": None,
            "suggested_description": None,
            "suggested_budget": None,
            "suggested_deadline": None,
            "suggested_requirements": None,
            "reasoning": response,
        }


@router.post("/conversations/suggest-message")
def suggest_conversation_message(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-274 — Suggest the first message for a new conversation.

    Analyzes the lead or customer context and suggests an appropriate
    opening message. Does NOT persist — returns only the suggestion.
    """
    # Build context from the entity being contacted
    context_parts = [f"Canal: {data.channel}"]

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
        context_parts.append(f"Tipo: Lead")
        context_parts.append(f"Nome: {lead.name}")
        if lead.phone:
            context_parts.append(f"Telefone: {lead.phone}")
        if lead.source:
            context_parts.append(f"Fonte: {lead.source}")
        if lead.interest:
            context_parts.append(f"Interesse: {lead.interest}")
    elif data.customer_id is not None:
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
        context_parts.append(f"Tipo: Customer")
        context_parts.append(f"Nome: {customer.name}")
        if customer.phone:
            context_parts.append(f"Telefone: {customer.phone}")
        if customer.email:
            context_parts.append(f"E-mail: {customer.email}")
    elif data.opportunity_id is not None:
        opp = db.scalar(
            select(Opportunity).where(
                Opportunity.id == data.opportunity_id,
                Opportunity.company_id == identity.company_id,
            )
        )
        if opp is None:
            raise HTTPException(
                status_code=404,
                detail="Opportunity not found",
            )
        context_parts.append(f"Tipo: Oportunidade")
        context_parts.append(f"Título: {opp.title}")
        if opp.description:
            context_parts.append(f"Descrição: {opp.description}")
        if opp.budget:
            context_parts.append(f"Orçamento: {opp.budget}")
        if opp.deadline:
            context_parts.append(f"Prazo: {opp.deadline}")
    else:
        raise HTTPException(
            status_code=400,
            detail="lead_id, customer_id, or opportunity_id is required",
        )

    context_text = "\n".join(context_parts)

    system_prompt = (
        "Com base nos dados deste contato, sugira uma primeira mensagem "
        "para iniciar uma conversa comercial.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"suggested_message": "mensagem de abertura profissional", '
        '"reasoning": "por que esta mensagem é adequada"}\n'
        "A mensagem deve ser profissional, personalizada e adequada ao canal."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=context_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    import json
    try:
        parsed = json.loads(response)
        return {
            "suggested_message": parsed.get("suggested_message", response),
            "reasoning": parsed.get("reasoning", response),
        }
    except (json.JSONDecodeError, AttributeError):
        return {
            "suggested_message": response,
            "reasoning": response,
        }


@router.post("/conversations/{conversation_id}/summarize")
def summarize_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """WP-270 — Generate an AI summary of the conversation.

    Analyzes all messages and returns a concise summary with key points
    and action items. Does NOT persist — returns only the summary.
    """
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

    if len(history_messages) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough messages to summarize",
        )

    # Build conversation text for the prompt
    prompt_parts = []
    for msg in history_messages:
        role = "Cliente" if msg.sender_type == "customer" else ("Humano" if msg.sender_type == "human" else "Agente" if msg.sender_type == "agent" else "Sistema")
        prompt_parts.append(f"{role}: {msg.content}")
    conversation_text = "\n".join(prompt_parts)

    system_prompt = (
        "Resuma esta conversa de forma concisa e útil para um operador de negócios.\n"
        "Retorne apenas JSON com esta estrutura:\n"
        '{"summary": "resumo em 2-3 frases", '
        '"key_points": ["ponto 1", "ponto 2"], '
        '"action_items": ["ação pendente 1"]}\n'
        "Se não houver pontos-chave ou ações pendentes, use listas vazias."
    )

    try:
        from app.routers.companies import _agent_config_store, _record_agent_call

        company_config = _agent_config_store.get(identity.company_id, {})
        effective_temp = company_config.get("temperature")
        effective_max_tokens = company_config.get("max_tokens")
        effective_model = company_config.get("model")

        response = generate_agent_reply(
            message=conversation_text,
            history=[],
            system_prompt=system_prompt,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
            model=effective_model,
        )
        _record_agent_call(identity.company_id, success=True)
    except AgentServiceError:
        _record_agent_call(identity.company_id, success=False)
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    # Try to parse JSON from response
    import json
    try:
        parsed = json.loads(response)
        return {
            "conversation_id": conversation.id,
            "summary": parsed.get("summary", response),
            "key_points": parsed.get("key_points", []),
            "action_items": parsed.get("action_items", []),
        }
    except (json.JSONDecodeError, AttributeError):
        # Fallback: return raw response as summary
        return {
            "conversation_id": conversation.id,
            "summary": response,
            "key_points": [],
            "action_items": [],
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
    lead_id: int | None = Query(None, description="Filter by lead"),
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

    if lead_id is not None:
        stmt = stmt.where(Conversation.lead_id == lead_id)

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
    lead_id: int | None = Query(None, description="Filter by lead"),
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

    if lead_id is not None:
        stmt = stmt.where(Conversation.lead_id == lead_id)

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
    lead_id: int | None = Query(None, description="Filter by lead"),
    from_date: str | None = Query(None, description="Filter created_at >= date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter created_at <= date (YYYY-MM-DD)"),
    sort: Literal["id", "last_message", "created_at"] = Query(default="id"),
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

    if lead_id is not None:
        stmt = stmt.where(Conversation.lead_id == lead_id)

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

    conversations = db.scalars(stmt).all()

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


# ---------------------------------------------------------------------------
# WP-180 — Bulk delete conversations
# ---------------------------------------------------------------------------


@router.post("/conversations/bulk-delete")
def bulk_delete_conversations(
    data: ConversationBulkDelete,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Bulk delete multiple conversations (tenant-isolated)."""
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.id.in_(data.conversation_ids),
            Conversation.company_id == identity.company_id,
        )
    ).all()

    deleted_ids = []
    for conv in conversations:
        db.delete(conv)
        deleted_ids.append(conv.id)

    db.commit()

    skipped = set(data.conversation_ids) - set(deleted_ids)

    return {
        "deleted": len(deleted_ids),
        "deleted_ids": sorted(deleted_ids),
        "skipped": sorted(skipped),
    }


@router.patch("/conversations/{conversation_id}/favorite")
def toggle_conversation_favorite(
    conversation_id: int,
    data: FavoriteToggle,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Toggle favorite status for a conversation."""
    conversation = _get_tenant_conversation(db, conversation_id, identity.company_id)

    key = (identity.company_id, "conversation", conversation_id)
    if data.favorited:
        from datetime import datetime, timezone
        _favorites_store[key] = {"favorited_at": datetime.now(timezone.utc)}
    else:
        _favorites_store.pop(key, None)

    favorited_at = _favorites_store.get(key, {}).get("favorited_at")
    return FavoriteResponse(
        entity_type="conversation",
        entity_id=conversation_id,
        favorited=data.favorited,
        favorited_at=favorited_at,
    )


# ---------------------------------------------------------------------------
# WP-543 — Auto-triage
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversation_id}/suggest-triage",
    response_model=TriageSuggestion,
)
def suggest_triage_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    """Suggest triage action for a conversation based on AI analysis."""
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

    try:
        result = _suggest_triage(history)
    except AgentServiceError:
        raise HTTPException(
            status_code=503,
            detail="Agent service unavailable",
        )

    return TriageSuggestion(
        next_action=result.get("next_action", "follow_up"),
        confidence=result.get("confidence", 0.5),
        reason=result.get("reason", "Análise automática"),
    )
