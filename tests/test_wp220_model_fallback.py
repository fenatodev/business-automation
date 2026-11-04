"""WP-220 — Explicit fallback when configured model doesn't exist on Ollama.

When a company configures a model that doesn't exist on the Ollama server,
the agent falls back to the default model instead of failing silently.
"""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.services.agent import generate_agent_reply, AgentServiceError
from app.database import settings


def test_fallback_when_custom_model_fails():
    """When custom model fails, agent falls back to default model."""
    call_count = 0

    def fake_post(url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        json_body = kwargs.get("json")
        if json_body and json_body.get("model") != settings.ollama_model:
            resp.raise_for_status.side_effect = httpx.HTTPError("Model not found")
            return resp
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"message": {"content": "Fallback response"}}
        return resp

    with patch("app.services.agent.httpx.post", side_effect=fake_post):
        result = generate_agent_reply(
            "Hello",
            [],
            model="nonexistent-model",
        )

    assert result == "Fallback response"
    assert call_count == 2


def test_no_fallback_when_using_default_model():
    """When already using default model, no fallback attempt."""
    def fake_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx.HTTPError("Default model failed")
        return resp

    with patch("app.services.agent.httpx.post", side_effect=fake_post):
        with pytest.raises(AgentServiceError, match="Ollama request failed"):
            generate_agent_reply(
                "Hello",
                [],
                model=settings.ollama_model,
            )


def test_no_fallback_when_model_is_none():
    """When model is None, no fallback attempt."""
    def fake_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx.HTTPError("Failed")
        return resp

    with patch("app.services.agent.httpx.post", side_effect=fake_post):
        with pytest.raises(AgentServiceError, match="Ollama request failed"):
            generate_agent_reply(
                "Hello",
                [],
                model=None,
            )


def test_fallback_uses_default_model_in_body():
    """The fallback request uses settings.ollama_model."""
    calls = []

    def fake_post(url, **kwargs):
        json_body = kwargs.get("json")
        calls.append(json_body.get("model") if json_body else None)
        resp = MagicMock()
        if len(calls) == 1:
            resp.raise_for_status.side_effect = httpx.HTTPError("Model not found")
            return resp
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"message": {"content": "OK"}}
        return resp

    with patch("app.services.agent.httpx.post", side_effect=fake_post):
        generate_agent_reply("Hello", [], model="custom-model")

    assert calls[0] == "custom-model"
    assert calls[1] == settings.ollama_model


def test_fallback_raises_when_default_also_fails():
    """If both custom and default model fail, raise AgentServiceError."""
    def fake_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx.HTTPError("All models failed")
        return resp

    with patch("app.services.agent.httpx.post", side_effect=fake_post):
        with pytest.raises(AgentServiceError, match="Ollama request failed"):
            generate_agent_reply("Hello", [], model="custom-model")


def test_no_fallback_when_custom_model_succeeds():
    """When custom model succeeds, no fallback is attempted."""
    call_count = 0

    def fake_post(url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"message": {"content": "Custom model response"}}
        return resp

    with patch("app.services.agent.httpx.post", side_effect=fake_post):
        result = generate_agent_reply("Hello", [], model="custom-model")

    assert result == "Custom model response"
    assert call_count == 1


def test_fallback_code_exists_in_agent():
    """The fallback logic exists in agent.py."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "WP-220" in code
    assert "fall back to the default model" in code
    assert 'body["model"] = settings.ollama_model' in code
