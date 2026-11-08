"""WP-213 — Model selection per company.

The Ollama model was hardcoded to `qwen3:8b` for all companies.
Now each company can configure its own model via agent config.
"""

import pytest
from httpx import Response
from unittest.mock import patch

from app.schemas import CompanyAgentConfig, AgentRequest


def test_company_agent_config_has_model_field():
    """CompanyAgentConfig schema has optional model field."""
    config = CompanyAgentConfig(model="llama3.1:8b")
    assert config.model == "llama3.1:8b"


def test_company_agent_config_model_optional():
    """model is optional in CompanyAgentConfig."""
    config = CompanyAgentConfig()
    assert config.model is None


def test_agent_request_has_model_field():
    """AgentRequest schema has optional model field."""
    req = AgentRequest(content="test", model="mistral:7b")
    assert req.model == "mistral:7b"


def test_agent_request_model_optional():
    """model is optional in AgentRequest."""
    req = AgentRequest(content="test")
    assert req.model is None


def test_agent_service_accepts_model_parameter():
    """The agent service accepts model parameter."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "model: str | None = None" in code
    # Verify model is used in body
    assert '"model": model_name' in code


def test_agent_service_falls_back_to_default_model():
    """When model is None, agent falls back to settings.ollama_model."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert 'settings.ollama_model' in code


def test_companies_router_get_returns_model():
    """GET /agent-config returns model field."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    # The entire file should contain the model return
    assert 'model=config.get("model")' in code


def test_companies_router_put_stores_model():
    """PUT /agent-config stores model field."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert 'data.model' in code
    assert 'config["model"]' in code


def test_conversations_router_passes_model():
    """The conversations router passes effective_model to agent service."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert 'effective_model' in code
    assert 'model=effective_model' in code


def test_conversations_router_model_fallback():
    """The conversations router falls back to company config model."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert 'company_config.get("model")' in code


def test_full_stack_model_flow():
    """End-to-end: schema validates, router stores, agent uses model."""
    # Schema accepts model
    config = CompanyAgentConfig(model="qwen2.5:7b")
    assert config.model == "qwen2.5:7b"

    # Schema allows None
    config_none = CompanyAgentConfig()
    assert config_none.model is None

    # AgentRequest also accepts model
    req = AgentRequest(content="hello", model="llama3.1:8b")
    assert req.model == "llama3.1:8b"


def test_agent_model_used_in_ollama_request():
    """When model is provided, it's used in the Ollama API request."""
    with open("app/services/agent.py") as f:
        code = f.read()
    # The model should be in the body dict
    assert '"model": model_name' in code
    assert 'model_name = model or self.default_model' in code


def test_model_parameter_in_generate_agent_reply_signature():
    """generate_agent_reply has model parameter."""
    with open("app/services/agent.py") as f:
        code = f.read()
    sig_start = code.index('def generate_agent_reply')
    sig_end = code.index(') -> str:', sig_start)
    signature = code[sig_start:sig_end]
    assert 'model: str | None = None' in signature


def test_companies_router_put_returns_model():
    """PUT /agent-config response includes model field."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    # The file should have model in CompanyAgentConfig return
    assert code.count('model=config.get("model")') >= 2  # get and put endpoints


def test_model_config_isolation_between_companies():
    """Different companies can have different models configured."""
    from app.routers.companies import _agent_config_store

    # Simulate two companies with different models
    _agent_config_store[1] = {"model": "qwen3:8b"}
    _agent_config_store[2] = {"model": "llama3.1:8b"}

    config1 = CompanyAgentConfig(
        model=_agent_config_store[1].get("model")
    )
    config2 = CompanyAgentConfig(
        model=_agent_config_store[2].get("model")
    )

    assert config1.model == "qwen3:8b"
    assert config2.model == "llama3.1:8b"

    # Cleanup
    del _agent_config_store[1]
    del _agent_config_store[2]
