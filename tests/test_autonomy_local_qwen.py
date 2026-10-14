"""Offline mocked tests for local Qwen draft generation. No network or costs."""

import json

import httpx
import pytest
from sqlalchemy.orm import Session

from app.services.autonomy_local_qwen import LocalQwenDraftComposer
from app.services.autonomy_core import prepare
from tests.test_autonomy_core import NOW, sandbox, policy, quote  # noqa: F401


def mock_transport(content, *, status=200):
    def handler(request: httpx.Request):
        assert request.url.scheme == "http"
        assert request.url.host == "127.0.0.1"
        assert request.url.port == 1251
        assert request.url.path == "/v1/chat/completions"
        data = json.loads(request.content)
        assert data["model"] == "qwen3.5-9b"
        assert data["stream"] is False
        assert "customer" not in json.dumps(data).lower()
        assert "quote-1" not in json.dumps(data)
        return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})

    return httpx.MockTransport(handler)


def test_local_model_produces_internal_quote_draft():
    llm = LocalQwenDraftComposer(transport=mock_transport(
        "Olá! Você tem alguma dúvida sobre o orçamento?"
    ))
    assert "orçamento" in llm("quote")


def test_local_model_produces_internal_inbound_draft():
    llm = LocalQwenDraftComposer(transport=mock_transport(
        "Olá! Qual serviço você busca e em qual região?"
    ))
    assert "região" in llm("inbound_lead")


@pytest.mark.parametrize("bad", [
    "<think>Internal reasoning</think> Olá!",
    "Conheça https://example.com",
    "A garantia será R$ 50",
    "Garantimos retorno.",
    "x" * 501,
    "",
])
def test_draft_rejects_unsafe_output(bad):
    llm = LocalQwenDraftComposer(transport=mock_transport(bad))
    with pytest.raises(RuntimeError, match="Unsafe"):
        llm("quote")


def test_provider_http_errors_do_not_leak_details():
    llm = LocalQwenDraftComposer(transport=mock_transport("", status=503))
    with pytest.raises(RuntimeError, match="Local model unavailable"):
        llm("quote")


def test_composer_has_no_unsupported_actions():
    llm = LocalQwenDraftComposer(transport=mock_transport("OK"))
    with pytest.raises(ValueError, match="Unsupported"):
        llm("unsupported")


def test_composer_requires_whitelisted_model():
    with pytest.raises(ValueError, match="tested local"):
        LocalQwenDraftComposer(model="cloud-or-paid-model")


def test_composer_integrates_only_after_policy_allows(sandbox, policy, quote):
    llm = LocalQwenDraftComposer(transport=mock_transport(
        "Olá! Tem alguma dúvida sobre o orçamento?"
    ))
    with Session(sandbox) as db:
        decision, _ = prepare(db, trusted_company_id=1, policy=policy,
                              signal=quote, now_ts=NOW, composer=llm)
        assert decision.state == "prepared"
        assert decision.draft.endswith("orçamento?")


def test_local_model_failure_escalates_without_outbox(sandbox, policy, quote):
    llm = LocalQwenDraftComposer(transport=mock_transport("R$ 999"))
    with Session(sandbox) as db:
        decision, _ = prepare(db, trusted_company_id=1, policy=policy,
                              signal=quote, now_ts=NOW, composer=llm)
        assert decision.state == "escalate"
        assert decision.reason == "model_unavailable"
        assert decision.draft is None
