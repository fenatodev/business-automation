"""WP-219 — Model validation in CompanyAgentConfig and AgentRequest.

The schema accepted any string for `model`. Now it rejects empty strings
and strings longer than 100 characters.
"""

import pytest
from pydantic import ValidationError

from app.schemas import CompanyAgentConfig, AgentRequest


def test_company_agent_config_model_accepts_valid_value():
    """CompanyAgentConfig accepts a valid model name."""
    config = CompanyAgentConfig(model="qwen3:8b")
    assert config.model == "qwen3:8b"


def test_company_agent_config_model_accepts_none():
    """CompanyAgentConfig model is optional."""
    config = CompanyAgentConfig()
    assert config.model is None


def test_company_agent_config_model_rejects_empty_string():
    """CompanyAgentConfig rejects empty model string."""
    with pytest.raises(ValidationError, match="model cannot be empty"):
        CompanyAgentConfig(model="")


def test_company_agent_config_model_rejects_whitespace_only():
    """CompanyAgentConfig rejects whitespace-only model string."""
    with pytest.raises(ValidationError, match="model cannot be empty"):
        CompanyAgentConfig(model="   ")


def test_company_agent_config_model_rejects_too_long():
    """CompanyAgentConfig rejects model names longer than 100 chars."""
    with pytest.raises(ValidationError, match="model name is too long"):
        CompanyAgentConfig(model="a" * 101)


def test_company_agent_config_model_accepts_100_chars():
    """CompanyAgentConfig accepts model names up to 100 chars."""
    config = CompanyAgentConfig(model="a" * 100)
    assert config.model == "a" * 100


def test_company_agent_config_model_strips_whitespace():
    """CompanyAgentConfig strips leading/trailing whitespace from model."""
    config = CompanyAgentConfig(model="  qwen3:8b  ")
    assert config.model == "qwen3:8b"


def test_agent_request_model_accepts_valid_value():
    """AgentRequest accepts a valid model name."""
    req = AgentRequest(content="test", model="llama3.1:8b")
    assert req.model == "llama3.1:8b"


def test_agent_request_model_accepts_none():
    """AgentRequest model is optional."""
    req = AgentRequest(content="test")
    assert req.model is None


def test_agent_request_model_rejects_empty_string():
    """AgentRequest rejects empty model string."""
    with pytest.raises(ValidationError, match="model cannot be empty"):
        AgentRequest(content="test", model="")


def test_agent_request_model_rejects_whitespace_only():
    """AgentRequest rejects whitespace-only model string."""
    with pytest.raises(ValidationError, match="model cannot be empty"):
        AgentRequest(content="test", model="   ")


def test_agent_request_model_rejects_too_long():
    """AgentRequest rejects model names longer than 100 chars."""
    with pytest.raises(ValidationError, match="model name is too long"):
        AgentRequest(content="test", model="a" * 101)


def test_agent_request_model_accepts_100_chars():
    """AgentRequest accepts model names up to 100 chars."""
    req = AgentRequest(content="test", model="a" * 100)
    assert req.model == "a" * 100


def test_agent_request_model_strips_whitespace():
    """AgentRequest strips leading/trailing whitespace from model."""
    req = AgentRequest(content="test", model="  mistral:7b  ")
    assert req.model == "mistral:7b"


def test_company_agent_config_model_validator_rejects_empty():
    """The model validator rejects empty strings via ValidationError."""
    with pytest.raises(ValidationError):
        CompanyAgentConfig(model="")


def test_agent_request_model_validator_rejects_empty():
    """The model validator rejects empty strings via ValidationError."""
    with pytest.raises(ValidationError):
        AgentRequest(content="test", model="")
