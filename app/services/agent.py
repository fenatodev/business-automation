import httpx

from app.database import settings


BASE_SYSTEM_PROMPT = (
    "Você é um agente de atendimento comercial. "
    "Responda em português brasileiro de forma objetiva, "
    "profissional e natural. "
    "Seu objetivo é entender a necessidade do cliente, "
    "tirar dúvidas e qualificar o lead. "
    "Não invente preços, serviços, prazos ou informações."
)


class AgentServiceError(RuntimeError):
    pass


def generate_agent_reply(
    message: str,
    history: list[dict],
    instructions: str | None = None,
    model: str | None = None,
) -> str:
    system_prompt = BASE_SYSTEM_PROMPT
    if instructions:
        system_prompt = f"{system_prompt}\n\nInstruções da empresa:\n{instructions}"

    messages = [
        {
            "role": "system",
            "content": system_prompt,
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

    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": model or settings.ollama_model,
                "messages": messages,
                "stream": False,
            },
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
