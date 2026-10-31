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


def generate_agent_reply(
    message: str,
    history: list[dict],
    system_prompt: str | None = None,
    temperature: float | None = None,
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
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }

    # WP-203 — Pass temperature to Ollama if specified
    if temperature is not None:
        body["options"] = {"temperature": temperature}

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
        data = response.json()
        content = data["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AgentServiceError("Invalid Ollama response") from exc

    if not isinstance(content, str):
        raise AgentServiceError("Invalid Ollama response")

    return content