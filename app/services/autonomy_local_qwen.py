"""Optional local-Qwen composer for *internal* drafts in the F2 simulation.

This adapter never contacts the customer or a paid/cloud model. It only calls
the existing llama.cpp OpenAI-compatible server on loopback. No customer text,
phone numbers, addresses, quotes or personal records are sent to the model.
"""

from __future__ import annotations

import httpx


class LocalQwenDraftComposer:
    """Small, bounded, replaceable language adapter; not an authorization source."""

    def __init__(
        self,
        *,
        model: str = "qwen3.5-9b",
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        if model != "qwen3.5-9b":
            raise ValueError("Only the tested local sandbox model is allowed")
        if timeout_seconds <= 0 or timeout_seconds > 60:
            raise ValueError("Invalid model timeout")
        self.model = model
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def __call__(self, kind: str) -> str:
        if kind not in ("quote", "inbound_lead"):
            raise ValueError("Unsupported commercial intent")

        # The prompt contains ONLY the class of a fictional scenario. No PII.
        intent = (
            "Crie uma única mensagem perguntando educadamente se a pessoa tem "
            "dúvidas sobre um orçamento já recebido."
            if kind == "quote"
            else "Crie uma única mensagem perguntando qual serviço a pessoa "
                 "precisa e em qual região."
        )
        request = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você prepara somente rascunhos internos em português brasileiro. "
                        "Responda com UMA frase curta e objetiva, texto puro, sem markdown. "
                        "Não invente preços, prazos, garantias, descontos, nomes ou links. "
                        "Não assuma autorização para entrar em contato. "
                        "Não descreva raciocínio nem inclua tags."
                    ),
                },
                {"role": "user", "content": intent},
            ],
            "max_tokens": 160,
            "temperature": 0.2,
            "stream": False,
        }
        try:
            with httpx.Client(
                base_url="http://127.0.0.1:1251/v1",
                timeout=self.timeout_seconds,
                transport=self.transport,
                trust_env=False,
            ) as client:
                response = client.post("/chat/completions", json=request)
                response.raise_for_status()
                payload = response.json()
                draft = payload["choices"][0]["message"]["content"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Local model unavailable or invalid reply") from exc

        if not isinstance(draft, str):
            raise RuntimeError("Invalid local model draft")
        draft = draft.strip()
        lowered = draft.lower()
        if (
            not draft
            or len(draft) > 500
            or "<think" in lowered
            or "</think" in lowered
            or "http://" in lowered
            or "https://" in lowered
            or "r$" in lowered
            or "€" in draft
            or "$" in draft
            or "garantimos" in lowered
            or any(ord(char) < 32 and char not in "\n\t" for char in draft)
        ):
            raise RuntimeError("Unsafe local model draft")

        return draft
