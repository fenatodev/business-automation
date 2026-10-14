"""Commercial intake core — pure, offline, simulation-only decision engine.

This module provides a deterministic triage function that receives a synthetic
commercial inquiry event and a candidate agent reply, then returns a structured
decision.  It never calls external services, sends messages, or writes to a
database.  ``can_send`` is always ``False`` in this package.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

_MAX_MESSAGE_LENGTH = 4000
_MAX_CANDIDATE_LENGTH = 2000
_MAX_CONTEXT_LENGTH = 2000


class CommercialIntakeEvent(BaseModel):
    """Represents a single inbound commercial inquiry (synthetic)."""

    channel: str = Field(min_length=1, max_length=30)
    message: str = Field(min_length=1, max_length=_MAX_MESSAGE_LENGTH)
    service_context: str = Field(min_length=1, max_length=_MAX_CONTEXT_LENGTH)
    event_id: str = Field(min_length=1, max_length=100)

    @field_validator("message")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        if any(c in v for c in ("\x00", "\x01", "\x1f")):
            raise ValueError("message contains control characters")
        return v.strip()


class CandidateReply(BaseModel):
    """Text candidate produced by a future LLM wrapper (injected, not called)."""

    text: str = Field(default="", max_length=_MAX_CANDIDATE_LENGTH)


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------


class IntakeDecision(BaseModel):
    """Structured, validated decision returned by the intake engine."""

    event_id: str
    intent: str = Field(default="unknown")
    next_step: str = Field(default="none")
    draft_reply: str = Field(default="")
    needs_human_review: bool = False
    can_send: bool = False
    flags: list[str] = Field(default_factory=list)
    simulation_only: bool = True


# ---------------------------------------------------------------------------
# Risk / policy helpers
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(sua[s]?|your?)\s+(regra|instru|rule|instruction)",
    r"desabilitar",
    r"bypass",
    r"contornar",
    r"jailbreak",
    r"mode\s*[:=]\s*(dev|admin|debug)",
    r"system\s*[:=]",
    r"<\s*\/?\s*(system|instruction|prompt)\s*>",
    r"role\s*[:=]\s*(admin|system|developer)",
]

_SENSITIVE_REQUEST_PATTERNS: list[str] = [
    r"(senha|password|credencial|credential|token|chave\s*api|api[_\s]?key)",
    r"(acesso\s*(admin|total|completo))",
    r"(cartão\s*crédito|credit\s*card|cpf|ssn)",
]

_FINANCIAL_COMMITMENT_PATTERNS: list[str] = [
    r"(preço|preco|valor|custo|custo|orçamento|orcamento|cobrar|charge|pricing)",
    r"(prazo|deadline|entrega\s*em|garantir\s*(prazo|data))",
    r"(roi|retorno\s*sobre|garantia\s*de\s*resultado)",
]


def _detect_flags(message: str, candidate: str) -> list[str]:
    """Return a list of risk flags found in the combined input text."""
    flags: list[str] = []
    combined = (message + " " + candidate).lower()

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, combined):
            flags.append("possible_prompt_injection")
            break

    for pattern in _SENSITIVE_REQUEST_PATTERNS:
        if re.search(pattern, combined):
            flags.append("asks_sensitive_data")
            break

    for pattern in _FINANCIAL_COMMITMENT_PATTERNS:
        if re.search(pattern, combined):
            flags.append("financial_commitment_request")
            break

    return flags


def _classify_intent(message: str) -> str:
    """Return a coarse intent label based on keyword heuristics."""
    lower = message.lower()
    if any(w in lower for w in ("automat", "integra", "fluxo", "processo", "robô", "bot")):
        return "automation_inquiry"
    if any(w in lower for w in ("site", "landing", "página", "pagina", "web")):
        return "web_inquiry"
    if any(w in lower for w in ("marketing", "anúncio", "anuncio", "divulgar")):
        return "marketing_inquiry"
    if any(w in lower for w in ("preço", "preco", "valor", "quanto", "custa")):
        return "pricing_inquiry"
    return "general_inquiry"


def _is_incomplete(message: str) -> bool:
    """Heuristic: message is too short or clearly lacks substance."""
    stripped = message.strip()
    if len(stripped.split()) < 4:
        return True
    if stripped.endswith("?") and len(stripped.split()) < 6:
        return True
    return False


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def process_commercial_intake(
    event: CommercialIntakeEvent,
    candidate: CandidateReply | None = None,
) -> IntakeDecision:
    """Produce a validated intake decision from a synthetic event.

    This is a **pure function**: no network calls, no database writes, no
    side effects.  The same inputs always produce the same output.

    Args:
        event: The inbound commercial inquiry event.
        candidate: Optional text candidate from a future LLM wrapper.
            If ``None`` or empty, the engine falls back to a safe default.

    Returns:
        An ``IntakeDecision`` with structured fields for downstream use.
    """
    flags = _detect_flags(event.message, candidate.text if candidate else "")
    intent = _classify_intent(event.message)
    incomplete = _is_incomplete(event.message)

    # --- Build or validate draft reply ---
    draft = ""
    if candidate and candidate.text.strip():
        draft = candidate.text.strip()[:_MAX_CANDIDATE_LENGTH]
    elif incomplete:
        draft = (
            "Para te ajudar melhor, poderia descrever com mais detalhes o que "
            "você precisa? Qual processo ou ferramenta está envolvida?"
        )
    else:
        draft = (
            "Entendi. Para prosseguir, qual processo você quer automatizar e "
            "qual ferramenta utiliza hoje?"
        )

    # --- Determine next step ---
    if "possible_prompt_injection" in flags:
        next_step = "escalate_to_human"
    elif incomplete:
        next_step = "ask_clarification"
    elif "financial_commitment_request" in flags:
        next_step = "ask_clarification"
    else:
        next_step = "ask_clarification"

    # --- Policy decisions ---
    needs_human = (
        "possible_prompt_injection" in flags
        or "asks_sensitive_data" in flags
        or "financial_commitment_request" in flags
    )

    return IntakeDecision(
        event_id=event.event_id,
        intent=intent,
        next_step=next_step,
        draft_reply=draft,
        needs_human_review=needs_human,
        can_send=False,
        flags=flags,
        simulation_only=True,
    )


def validate_intake_event(data: dict[str, Any]) -> CommercialIntakeEvent:
    """Validate raw dict input and return a typed event, or raise."""
    return CommercialIntakeEvent(**data)
