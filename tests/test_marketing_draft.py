"""WP-022 — no actual model, public network, customer DB or publishing in tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from marketing.draft import (
    ALLOWED_CHANNEL,
    DEFAULT_ENDPOINT,
    DraftError,
    _validate_model_content,
    _valid_endpoint,
    build_messages,
    generate_draft,
    load_source,
    save_private,
)


POST = (
    "Um pedido fictício vira um registro em um CRM simulado. "
    "Nesta demonstração offline em Python, o código testa duplicações, "
    "conflitos e resultados incertos. Não há integração com cliente real "
    "nem medição de ganhos comerciais. Veja o código e os testes: "
    "https://github.com/fenatodev/business-automation/tree/main/examples"
)
IDS = ["demo_offline", "demo_safety", "demo_limit"]


def model_response(
    post: str = POST,
    ids: list[str] | None = None,
) -> dict:
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {"post": post, "used_fact_ids": IDS if ids is None else ids},
                    ensure_ascii=False,
                ),
            }
        }]
    }


def transport_that_replies(payload: dict | None = None, *, code: int = 200):
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(code, json=model_response() if payload is None else payload)

    return httpx.MockTransport(handler), calls


def test_approved_source_is_repo_curated_public_and_fully_labeled() -> None:
    source = load_source("synthetic-order-crm")
    assert source["classification"] == "public_synthetic"
    assert source["url"].startswith("https://github.com/fenatodev/")
    assert {f["id"] for f in source["facts"]} == {
        "demo_offline", "demo_safety", "demo_tests", "demo_limit"
    }


def test_unknown_source_is_rejected_before_a_model_call() -> None:
    with pytest.raises(DraftError, match="fonte_publica_nao_aprovada"):
        generate_draft(source_id="../../secrets.env")


@pytest.mark.parametrize("endpoint", [
    "https://api.example.com/v1/chat/completions",
    "http://localhost:1251/v1/chat/completions",
    "http://10.0.0.1:1251/v1/chat/completions",
    "http://127.0.0.1:1251/v1/models",
    "http://127.0.0.1:1251/v1/chat/completions?secret=1",
    "http://user:password@127.0.0.1:1251/v1/chat/completions",
    "http://127.0.0.1:1251/v1/chat/completions#fragment",
    "file:///tmp/socket",
    "http://127.0.0.1/v1/chat/completions",
])
def test_only_explicit_loopback_model_endpoint_is_permitted(endpoint: str) -> None:
    with pytest.raises(DraftError):
        _valid_endpoint(endpoint)


def test_model_prompt_is_short_explicit_and_restricts_authority() -> None:
    messages = build_messages(load_source("synthetic-order-crm"))
    assert len(messages) == 2
    assert [item["role"] for item in messages] == ["system", "user"]
    content = " ".join(item["content"] for item in messages)
    for fragment in ("pt-BR", "LinkedIn", "JSON", "demonstração", "demo_offline",
                     "demo_limit", "Não invente clientes", "dados fictícios"):
        assert fragment in content
    assert "localhost" not in content and "DATABASE_URL" not in content


def test_preview_cli_does_not_call_provider_or_save_files() -> None:
    run = subprocess.run(
        [sys.executable, "-m", "marketing.draft", "--preview"],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(run.stdout)
    assert result["mode"] == "preview_only"
    assert result["published"] is False
    assert result["source_id"] == "synthetic-order-crm"
    assert run.stderr == ""


def test_generate_calls_one_local_model_without_credentials_or_remote_upload() -> None:
    transport, calls = transport_that_replies()
    record = generate_draft(transport=transport)
    assert len(calls) == 1
    request = calls[0]
    assert str(request.url) == DEFAULT_ENDPOINT
    assert "authorization" not in request.headers
    body = json.loads(request.content)
    assert body["model"] == "qwen3.5-9b"
    assert body["response_format"] == {"type": "json_object"}
    assert body["stream"] is False
    assert len(body["messages"]) == 2
    assert "99freelas" not in request.content.decode("utf-8")
    assert record["status"] == "pending_review"
    assert record["review_required"] is True
    assert record["approved"] is False and record["published"] is False
    assert record["channel"] == ALLOWED_CHANNEL
    assert record["post"] == POST
    assert record["used_fact_ids"] == IDS
    assert len(record["review_checks"]) >= 4
    assert record["source_url"] == load_source("synthetic-order-crm")["url"]


def test_no_retry_on_timeout_or_failed_model_response() -> None:
    count = 0

    def timeout(_request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(DraftError, match="modelo_local_indisponivel"):
        generate_draft(transport=httpx.MockTransport(timeout))
    assert count == 1

    transport, calls = transport_that_replies(code=503)
    with pytest.raises(DraftError, match="modelo_local_indisponivel"):
        generate_draft(transport=transport)
    assert len(calls) == 1


def test_http_redirect_is_not_followed() -> None:
    calls = []

    def redirect(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://example.com/"})

    with pytest.raises(DraftError):
        generate_draft(transport=httpx.MockTransport(redirect))
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [
    {},
    {"choices": []},
    {"choices": [{"message": {}}]},
    {"choices": [{"message": {"content": ""}}]},
    {"choices": [{"message": {"content": "{\"post\":\"oi\"}"}}]},
    {"choices": [{"message": {"content": "not json"}}]},
])
def test_invalid_provider_content_never_becomes_a_draft(payload: dict) -> None:
    transport, calls = transport_that_replies(payload)
    with pytest.raises(DraftError):
        generate_draft(transport=transport)
    assert len(calls) == 1


@pytest.mark.parametrize("post", [
    "Um exemplo offline: atendemos nossos clientes com integração real.",
    "Nossa demo fictícia garantimos resultados e ROI mensurado. " + ("a" * 40),
    "A demonstração offline gerou 99% de economia. " + ("a" * 35),
    "Nossa demo offline vale R$ 10000 e não há riscos. " + ("a" * 35),
    "Nosso exemplo offline exige visitar https://evil.example/promo",
    "<script>alert(1)</script> Veja a demonstração offline em Python." + ("a" * 30),
])
def test_unsourced_commercial_claims_or_external_links_are_blocked(post: str) -> None:
    transport, _ = transport_that_replies(model_response(post))
    with pytest.raises(DraftError):
        generate_draft(transport=transport)


@pytest.mark.parametrize("ids", [
    [],
    ["demo_offline"],
    ["demo_limit"],
    ["demo_offline", "demo_limit", "fake_claim"],
    ["demo_offline", "demo_offline", "demo_limit"],
])
def test_missing_unknown_or_repeated_claim_ids_are_rejected(ids: list[str]) -> None:
    with pytest.raises(DraftError):
        _validate_model_content(
            json.dumps({"post": POST, "used_fact_ids": ids}),
            load_source("synthetic-order-crm"),
        )


def test_private_queue_creates_secure_non_overwriting_pending_drafts(tmp_path: Path) -> None:
    client0 = tmp_path / "client0"
    client0.mkdir(mode=0o700)
    record = generate_draft(transport=transport_that_replies()[0])
    first = save_private(record, client0_dir=client0)
    second = save_private(record, client0_dir=client0)

    assert first != second and first.parent == client0 / "marketing-drafts"
    assert (first.parent.stat().st_mode & 0o777) == 0o700
    for path in (first, second):
        assert path.is_file()
        assert (path.stat().st_mode & 0o777) == 0o600
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["status"] == "pending_review"
        assert data["approved"] is False and data["published"] is False
        assert data["post"] == POST


def test_refuses_unsafe_private_area_or_symlink(tmp_path: Path) -> None:
    record = generate_draft(transport=transport_that_replies()[0])

    world_readable = tmp_path / "world-readable"
    world_readable.mkdir(mode=0o755)
    with pytest.raises(DraftError, match="diretorio_privado_inseguro"):
        save_private(record, client0_dir=world_readable)

    safe = tmp_path / "safe"
    safe.mkdir(mode=0o700)
    (safe / "marketing-drafts").symlink_to(world_readable, target_is_directory=True)
    with pytest.raises(DraftError, match="diretorio_privado_inseguro"):
        save_private(record, client0_dir=safe)


@pytest.mark.parametrize("changed", [
    {"status": "approved"},
    {"approved": True},
    {"published": True},
])
def test_only_pending_unapproved_drafts_can_be_saved(tmp_path: Path, changed: dict) -> None:
    base = tmp_path / "client0"
    base.mkdir(mode=0o700)
    record = generate_draft(transport=transport_that_replies()[0])
    record.update(changed)
    with pytest.raises(DraftError, match="somente_rascunhos_pendentes"):
        save_private(record, client0_dir=base)
    assert list((base / "marketing-drafts").iterdir()) == []


def test_generate_flag_required_for_private_write() -> None:
    run = subprocess.run(
        [sys.executable, "-m", "marketing.draft", "--save-private"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2
    assert "--save-private exige --generate" in run.stderr
