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


def summarize_conversation(
    history: list[dict],
    model: str | None = None,
) -> dict:
    """Generate a summary of a conversation history via Ollama.

    Returns a dict with 'summary', 'key_points' and 'action_items'.
    Raises AgentServiceError on failure.
    """
    messages = [
        {
            "role": "system",
            "content": _SUMMARY_SYSTEM_PROMPT,
        }
    ]

    role_map = {
        "customer": "user",
        "agent": "assistant",
        "human": "assistant",
        "system": "system",
    }

    for item in history:
        messages.append(
            {
                "role": role_map.get(
                    item["sender_type"],
                    "user",
                ),
                "content": item["content"],
            }
        )

    messages.append(
        {
            "role": "user",
            "content": "Resuma a conversa acima.",
        }
    )

    body: dict[str, object] = {
        "model": model if model else settings.ollama_model,
        "messages": messages,
        "stream": False,
    }

    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/chat",
            json=body,
            timeout=120,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AgentServiceError("Ollama request failed") from exc

    try:
        raw = response.json()
        content = raw["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AgentServiceError("Invalid Ollama response") from exc

    if not isinstance(content, str):
        raise AgentServiceError("Invalid Ollama response")

    # Parse JSON from the response; fall back to plain text summary
    import json

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return {
                "summary": parsed.get("summary", content),
                "key_points": parsed.get("key_points", []),
                "action_items": parsed.get("action_items", []),
            }
    except json.JSONDecodeError:
        pass

    # If JSON parsing fails, return the raw content as summary
    return {
        "summary": content,
        "key_points": [],
        "action_items": [],
    }


def generate_agent_reply(
    message: str,
    history: list[dict],
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    # WP-202 — Allow custom system prompt; falls back to default
    prompt = system_prompt if system_prompt else _DEFAULT_SYSTEM_PROMPT

    messages = [
        {
            "role": "system",
            "content": prompt,
        }
    ]

    role_map = {
        "customer": "user",
        "agent": "assistant",
        "human": "assistant",
        "system": "system",
    }

    for item in history:
        messages.append(
            {
                "role": role_map.get(
                    item["sender_type"],
                    "user",
                ),
                "content": item["content"],
            }
        )

    messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    # Build request body
    body: dict[str, object] = {
        "model": model if model else settings.ollama_model,
        "messages": messages,
        "stream": False,
    }

    # WP-203 — Pass temperature to Ollama if specified
    # WP-208 — Pass max_tokens to Ollama if specified
    options: dict[str, object] = {}
    if temperature is not None:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    if options:
        body["options"] = options

    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/chat",
            json=body,
            timeout=120,
        )

        response.raise_for_status()
    except httpx.HTTPError as exc:
        # WP-220 — If model-specific request fails and we used a custom model,
        # fall back to the default model once.
        if model and model != settings.ollama_model:
            body["model"] = settings.ollama_model
            try:
                response = httpx.post(
                    f"{settings.ollama_url}/api/chat",
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