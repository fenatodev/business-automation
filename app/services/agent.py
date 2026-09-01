import httpx

from app.database import settings


def generate_agent_reply(
    message: str,
    history: list[dict],
) -> str:

    messages = [
        {
            "role": "system",
            "content": (
                "Você é um agente de atendimento comercial. "
                "Responda em português brasileiro de forma objetiva, "
                "profissional e natural. "
                "Seu objetivo é entender a necessidade do cliente, "
                "tirar dúvidas e qualificar o lead. "
                "Não invente preços, serviços, prazos ou informações."
            ),
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

    response = httpx.post(
        f"{settings.ollama_url}/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]