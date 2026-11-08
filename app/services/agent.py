import json as _json
from abc import ABC, abstractmethod

import httpx

from app.database import settings


class AgentServiceError(RuntimeError):
    pass


_DEFAULT_SYSTEM_PROMPT = (
    "Você é um agente de atendimento comercial. "
    "Responda em português brasileiro de forma objetiva, "
    "profissional e natural. "
    "Seu objetivo é entender a necessidade do cliente, "
    "tirar dúvidas e qualificar o lead. "
    "Não invente preços, serviços, prazos ou informações."
)


_SUMMARY_SYSTEM_PROMPT = (
    "Resuma a conversa a seguir em português brasileiro. "
    "Retorne um JSON com as chaves 'summary' (texto curto), "
    "'key_points' (lista de pontos-chave) e "
    "'action_items' (lista de ações pendentes, se houver). "
    "Se não houver ações pendentes, use lista vazia."
)


class AgentProvider(ABC):
    """Abstract interface for AI agent providers."""

    @abstractmethod
    def generate_reply(
        self,
        message: str,
        history: list[dict],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        """Generate an agent reply to a customer message."""

    @abstractmethod
    def summarize(
        self,
        history: list[dict],
        model: str | None = None,
    ) -> dict:
        """Summarize a conversation history.

        Returns a dict with 'summary', 'key_points' and 'action_items'.
        """

    @abstractmethod
    def health_check(self) -> dict:
        """Check if the provider is available.

        Returns a dict with 'provider', 'status' and optional 'details'.
        """


class OllamaProvider(AgentProvider):
    """Ollama-based agent provider."""

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
    ):
        self.base_url = base_url or settings.ollama_url
        self.default_model = default_model or settings.ollama_model

    def _build_messages(
        self,
        system_prompt: str,
        history: list[dict],
        user_message: str,
    ) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        role_map = {
            "customer": "user",
            "agent": "assistant",
            "human": "assistant",
            "system": "system",
        }
        for item in history:
            messages.append(
                {
                    "role": role_map.get(item["sender_type"], "user"),
                    "content": item["content"],
                }
            )
        messages.append({"role": "user", "content": user_message})
        return messages

    def _chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        model_name = model or self.default_model
        body: dict[str, object] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }
        options: dict[str, object] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            body["options"] = options

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=body,
                timeout=120,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # WP-220 — fallback to default model if custom model fails
            if model and model != self.default_model:
                body["model"] = self.default_model
                try:
                    response = httpx.post(
                        f"{self.base_url}/api/chat",
                        json=body,
                        timeout=120,
                    )
                    response.raise_for_status()
                except httpx.HTTPError as fallback_exc:
                    raise AgentServiceError("Ollama request failed") from fallback_exc
            else:
                raise AgentServiceError("Ollama request failed") from exc

        try:
            data = response.json()
            content = data["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AgentServiceError("Invalid Ollama response") from exc

        if not isinstance(content, str):
            raise AgentServiceError("Invalid Ollama response")
        return content

    def generate_reply(
        self,
        message: str,
        history: list[dict],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT
        messages = self._build_messages(prompt, history, message)
        return self._chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)

    def summarize(
        self,
        history: list[dict],
        model: str | None = None,
    ) -> dict:
        messages = [{"role": "system", "content": _SUMMARY_SYSTEM_PROMPT}]
        role_map = {
            "customer": "user",
            "agent": "assistant",
            "human": "assistant",
            "system": "system",
        }
        for item in history:
            messages.append(
                {
                    "role": role_map.get(item["sender_type"], "user"),
                    "content": item["content"],
                }
            )
        messages.append({"role": "user", "content": "Resuma a conversa acima."})

        content = self._chat(messages, model=model)

        # Parse JSON from the response; fall back to plain text summary
        try:
            parsed = _json.loads(content)
            if isinstance(parsed, dict):
                return {
                    "summary": parsed.get("summary", content),
                    "key_points": parsed.get("key_points", []),
                    "action_items": parsed.get("action_items", []),
                }
        except _json.JSONDecodeError:
            pass

        return {
            "summary": content,
            "key_points": [],
            "action_items": [],
        }

    def health_check(self) -> dict:
        try:
            response = httpx.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            response.raise_for_status()
            return {
                "provider": "ollama",
                "status": "healthy",
                "details": {"base_url": self.base_url},
            }
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            return {
                "provider": "ollama",
                "status": "unhealthy",
                "details": {"error": str(exc)},
            }


class NoopProvider(AgentProvider):
    """No-op provider that returns placeholder responses (for testing/fallback)."""

    def generate_reply(
        self,
        message: str,
        history: list[dict],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        return "[Agente indisponível — resposta automática desativada]"

    def summarize(
        self,
        history: list[dict],
        model: str | None = None,
    ) -> dict:
        return {
            "summary": "[Resumo indisponível — agente desativado]",
            "key_points": [],
            "action_items": [],
        }

    def health_check(self) -> dict:
        return {
            "provider": "noop",
            "status": "healthy",
            "details": {"note": "No-op provider always healthy"},
        }


# ---------------------------------------------------------------------------
# Provider registry & factory
# ---------------------------------------------------------------------------

_available_providers: dict[str, AgentProvider] = {}


def register_provider(name: str, provider: AgentProvider) -> None:
    """Register an agent provider by name."""
    _available_providers[name] = provider


def get_provider(name: str | None = None) -> AgentProvider:
    """Get an agent provider by name, falling back to the default."""
    if name and name in _available_providers:
        return _available_providers[name]
    return _available_providers.get(
        "default",
        _available_providers.get("ollama", NoopProvider()),
    )


def _ensure_default_provider() -> None:
    """Ensure default providers are registered.

    If Ollama is unavailable, fall back to NoopProvider as the default
    so that the API still returns 200 with placeholder responses instead
    of 503 on every call.
    """
    if not _available_providers:
        ollama = OllamaProvider()
        noop = NoopProvider()
        register_provider("ollama", ollama)
        register_provider("noop", noop)
        # Check if Ollama is reachable; use NoopProvider as default if not
        health = ollama.health_check()
        if health.get("status") == "healthy":
            register_provider("default", ollama)
        else:
            register_provider("default", noop)


# ---------------------------------------------------------------------------
# Public functions (backward compatible)
# ---------------------------------------------------------------------------


def summarize_conversation(
    history: list[dict],
    model: str | None = None,
) -> dict:
    """Generate a summary of a conversation history.

    Returns a dict with 'summary', 'key_points' and 'action_items'.
    Raises AgentServiceError on failure.
    """
    _ensure_default_provider()
    provider = get_provider()
    return provider.summarize(history, model=model)


def generate_agent_reply(
    message: str,
    history: list[dict],
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    """Generate an agent reply to a customer message."""
    _ensure_default_provider()
    provider = get_provider()
    return provider.generate_reply(
        message,
        history,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )