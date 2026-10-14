"""Candidate generator for commercial intake — pluggable LLM interface.

This module provides a small, replaceable port for generating text candidates
that feed into the WP-035 commercial intake engine.  It supports a static
deterministic generator for demos and tests, and an Ollama-backed generator
that injects its HTTP client and enforces loopback-only URLs.

No external service is started, no model is downloaded, and no real AI call
is executed during tests or demos.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Protocol

import httpx

from app.services.commercial_intake import (
    CandidateReply,
    CommercialIntakeEvent,
    IntakeDecision,
    process_commercial_intake,
)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class CandidateGenerationError(RuntimeError):
    """Raised when candidate generation fails.

    The message is sanitised and never leaks prompt text, client data,
    internal stack traces, or HTTP response bodies.
    """

    def __init__(self, message: str = "candidate generation failed") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Port / interface
# ---------------------------------------------------------------------------


class CandidateGenerator(Protocol):
    """Replaceable interface for producing a candidate reply."""

    def generate(self, event: CommercialIntakeEvent) -> CandidateReply:
        """Return a candidate text reply for *event*.

        Implementations must raise ``CandidateGenerationError`` on failure
        rather than leaking internal details.
        """
        ...


# ---------------------------------------------------------------------------
# Static candidate generator (deterministic, no network)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Você é um assistente de atendimento comercial. "
    "Responda em português brasileiro de forma objetiva e profissional. "
    "Seu objetivo é entender a necessidade do cliente e solicitar dados "
    "para qualificação. "
    "Não invente preços, prazos, garantias ou informações que não possui."
)


def _build_static_reply(event: CommercialIntakeEvent) -> str:
    """Build a deterministic clarification reply from the event."""
    messages = event.message.strip().lower()
    if any(w in messages for w in ("automat", "integra", "fluxo", "processo")):
        return (
            "Entendi que você tem interesse em automação. "
            "Para eu direcionar melhor, qual processo específico você quer "
            "automatizar e qual ferramenta utiliza hoje?"
        )
    if any(w in messages for w in ("site", "landing", "pagina", "página", "web")):
        return (
            "Vi que você menciona site ou presença web. "
            "Poderia descrever o objetivo principal do projeto e o público "
            "alvo que deseja atingir?"
        )
    if any(w in messages for w in ("marketing", "anúncio", "anuncio", "divulgar")):
        return (
            "Entendi o interesse em marketing. "
            "Para qualificar melhor, qual canal você utiliza hoje e qual "
            "resultado espera alcançar?"
        )
    return (
        "Obrigado pelo contato. Para eu ajudar da melhor forma, "
        "poderia descrever com mais detalhes o que você precisa? "
        "Qual processo ou ferramenta está envolvida?"
    )


class StaticCandidateGenerator:
    """Deterministic generator that produces clarification questions.

    This implementation makes no network calls and is safe for demos
    and unit tests.
    """

    def generate(self, event: CommercialIntakeEvent) -> CandidateReply:
        return CandidateReply(text=_build_static_reply(event))


# ---------------------------------------------------------------------------
# Ollama candidate generator (local-only, injected transport)
# ---------------------------------------------------------------------------

_LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "[::1]"}

_MAX_OLLAMA_RESPONSE_BODY = 64 * 1024  # 64 KiB guard


def _is_loopback_url(url: str) -> bool:
    """Return True only when *url* points to a loopback address."""
    try:
        # Strip protocol
        netloc = url.split("://", 1)[-1].split("/", 1)[0]
    except (AttributeError, IndexError):
        return False

    # Handle IPv6 bracket notation: [::1]:11434 -> ::1
    if netloc.startswith("["):
        bracket_end = netloc.find("]")
        if bracket_end == -1:
            return False
        host = netloc[1:bracket_end]
    else:
        # IPv4 or hostname: host:port
        host = netloc.rsplit(":", 1)[0]

    if host in _LOOPBACK_HOSTNAMES:
        return True

    # Check numeric IPs
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_loopback
    except ValueError:
        pass

    return False


def _sanitise_error(exc: Exception) -> str:
    """Return a safe error message that never leaks sensitive data."""
    return "candidate generation failed"


class OllamaCandidateGenerator:
    """Ollama-backed candidate generator with injected HTTP client.

    The model is fixed by the operator at construction time and never
    derived from client input.  The base URL must resolve to loopback.

    Args:
        client: An ``httpx.Client`` instance (allowing mock transport in
            tests).  Must not follow redirects.
        model: The Ollama model identifier, e.g. ``"qwen3:8b"``.
        base_url: The Ollama base URL.  Must be loopback-only.
        system_prompt: Trusted operator-configured system prompt.
        timeout: Request timeout in seconds.

    Raises:
        ValueError: If *base_url* is not a loopback address.
        CandidateGenerationError: If generation fails at runtime.
    """

    def __init__(
        self,
        client: httpx.Client,
        model: str = "qwen3:8b",
        base_url: str = "http://127.0.0.1:11434",
        system_prompt: str = _SYSTEM_PROMPT,
        timeout: float = 30.0,
    ) -> None:
        # Reject URLs with credentials, query strings, or fragments FIRST
        parsed = httpx.URL(base_url)
        if parsed.scheme != "http":
            raise ValueError("Ollama base_url must use plain HTTP on loopback")
        if parsed.username or parsed.password:
            raise ValueError("Ollama base_url must not contain credentials")
        if parsed.query or parsed.fragment:
            raise ValueError("Ollama base_url must not contain query or fragment")
        if parsed.path not in ("", "/"):
            raise ValueError("Ollama base_url must not contain a path")
        if not _is_loopback_url(base_url):
            raise ValueError("Ollama base_url must be loopback-only")
        if not model.strip() or len(model) > 120:
            raise ValueError("Ollama model must be a non-empty operator value")
        if not system_prompt.strip() or len(system_prompt) > 4000:
            raise ValueError("system_prompt must be a bounded operator value")
        if timeout <= 0 or timeout > 120:
            raise ValueError("timeout must be between 0 and 120 seconds")

        self._client = client
        self._model = model.strip()
        self._base_url = base_url.rstrip("/")
        self._system_prompt = system_prompt.strip()
        self._timeout = timeout

    def generate(self, event: CommercialIntakeEvent) -> CandidateReply:
        """Generate a candidate reply via Ollama /api/chat.

        Raises ``CandidateGenerationError`` on any failure, with a
        sanitised message.
        """
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": event.message},
        ]

        try:
            response = self._client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                },
                timeout=self._timeout,
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            raise CandidateGenerationError("Ollama request timed out")
        except httpx.NetworkError:
            raise CandidateGenerationError("Ollama service unavailable")
        except httpx.HTTPError:
            raise CandidateGenerationError("Ollama request failed")

        # Validate status
        if response.status_code < 200 or response.status_code >= 300:
            raise CandidateGenerationError(
                f"Ollama returned HTTP {response.status_code}"
            )

        # Guard against enormous response bodies
        raw = response.content
        if len(raw) > _MAX_OLLAMA_RESPONSE_BODY:
            raise CandidateGenerationError("Ollama response too large")

        # Parse JSON structure
        try:
            data = response.json()
        except (ValueError, TypeError):
            raise CandidateGenerationError("Invalid Ollama response format")

        # Extract message content
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError):
            raise CandidateGenerationError("Missing message in Ollama response")

        if not isinstance(content, str):
            raise CandidateGenerationError("Ollama content is not a string")

        content = content.strip()
        if not content:
            raise CandidateGenerationError("Ollama returned empty content")

        return CandidateReply(text=content)


# ---------------------------------------------------------------------------
# High-level evaluation function
# ---------------------------------------------------------------------------


def evaluate_intake(
    event: CommercialIntakeEvent,
    generator: CandidateGenerator,
) -> IntakeDecision:
    """Generate a candidate reply then run the intake decision engine.

    This function:
    1. Calls *generator.generate(event)* to obtain a candidate reply.
    2. Passes the candidate to ``process_commercial_intake``.
    3. On generation failure, returns a safe fallback decision with
       ``needs_human_review=True``, ``can_send=False``, and
       ``simulation_only=True``.

    The returned ``IntakeDecision`` is never mutated after creation.
    """
    try:
        candidate = generator.generate(event)
    except CandidateGenerationError:
        # Safe fallback when provider is unavailable
        fallback = process_commercial_intake(event, None)
        flags = list(fallback.flags)
        if "provider_unavailable" not in flags:
            flags.append("provider_unavailable")
        return IntakeDecision(
            event_id=event.event_id,
            intent=fallback.intent,
            next_step="ask_clarification",
            draft_reply=(
                "Não foi possível gerar um rascunho automático com segurança. "
                "Esta solicitação requer revisão humana antes de qualquer resposta."
            ),
            needs_human_review=True,
            can_send=False,
            flags=flags,
            simulation_only=True,
        )

    return process_commercial_intake(event, candidate)
