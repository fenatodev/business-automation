"""WP-237 — AI-assisted triage suggestion for opportunities.

The operator can ask the AI agent to suggest the next triage action
based on the opportunity context. The endpoint does NOT persist the suggestion.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from app.models import Company, Opportunity
from app.services.agent import AgentServiceError
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


@pytest.fixture
def company_b():
    with TestingSessionLocal() as db:
        db.add(Company(id=2, name="Synthetic B", slug="synthetic-b"))
        db.commit()


@pytest.fixture
def opportunity_a(company_a):
    """Create an opportunity in company A."""
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=1,
            source="intake",
            external_url="https://example.com/triage-test",
            title="Site institucional",
            description="Cliente precisa de site institucional moderno",
            budget="R$ 10.000",
            deadline="2026-12-31",
            requirements="WordPress, responsivo",
            captured_at=datetime.now(),
            next_action="pending",
        ))
        db.commit()


@pytest.fixture
def opportunity_b(company_b):
    """Create an opportunity in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=2,
            source="manual",
            external_url="https://example.com/other-tenant",
            title="Other tenant opportunity",
            description="Should not be accessible",
            captured_at=datetime.now(),
            next_action="pending",
        ))
        db.commit()


def test_endpoint_exists():
    """Endpoint is registered in the router."""
    with open("app/routers/opportunities.py") as f:
        content = f.read()
    assert '"/opportunities/{opportunity_id}/suggest-triage"' in content


def test_suggest_triage_returns_json(client, operator_a_headers, opportunity_a):
    """Suggest triage returns valid JSON response."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.return_value = json.dumps({
            "action": "prepare_proposal",
            "reasoning": "Oportunidade clara com orçamento e prazo definidos",
            "confidence": 0.85,
        })

        response = client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["suggested_action"] == "prepare_proposal"
    assert "reasoning" in data
    assert data["confidence"] == 0.85


def test_suggest_triage_uses_system_prompt(client, operator_a_headers, opportunity_a):
    """Suggest triage uses triage system prompt."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.return_value = json.dumps({
            "action": "follow",
            "reasoning": "Needs more information",
            "confidence": 0.6,
        })

        client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    mock_agent.assert_called_once()
    call_kwargs = mock_agent.call_args[1]
    assert call_kwargs["system_prompt"] is not None
    assert "triagem" in call_kwargs["system_prompt"].lower()


def test_suggest_triage_503_on_agent_failure(client, operator_a_headers, opportunity_a):
    """Suggest triage returns 503 when agent service fails."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.side_effect = AgentServiceError("Ollama request failed")

        response = client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    assert response.status_code == 503
    assert "indisponível" in response.json()["detail"].lower()


def test_suggest_triage_tenant_isolation(client, operator_a_headers, opportunity_b):
    """Suggest triage is tenant-isolated."""
    response = client.post(
        "/opportunities/1/suggest-triage",
        headers=operator_a_headers,
    )
    assert response.status_code == 404


def test_suggest_triage_requires_auth(client, opportunity_a):
    """Suggest triage requires authentication."""
    response = client.post(
        "/opportunities/1/suggest-triage",
    )
    assert response.status_code in (401, 403)


def test_suggest_triage_invalid_json_fallback(client, operator_a_headers, opportunity_a):
    """Suggest triage handles invalid JSON response gracefully."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.return_value = "Não consegui analisar esta oportunidade."

        response = client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["suggested_action"] == "pending"
    assert "raw_response" in data


def test_suggest_triage_invalid_action_fallback(client, operator_a_headers, opportunity_a):
    """Suggest triage falls back to pending for invalid action."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.return_value = json.dumps({
            "action": "invalid_action",
            "reasoning": "Some reasoning",
            "confidence": 0.5,
        })

        response = client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["suggested_action"] == "pending"


def test_suggest_triage_builds_prompt_with_context(client, operator_a_headers, opportunity_a):
    """Suggest triage builds prompt with all opportunity context."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.return_value = json.dumps({
            "action": "follow",
            "reasoning": "Test",
            "confidence": 0.7,
        })

        client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    message = mock_agent.call_args[1]["message"]
    assert "Site institucional" in message
    assert "site institucional moderno" in message
    assert "R$ 10.000" in message
    assert "2026-12-31" in message
    assert "WordPress, responsivo" in message


def test_suggest_triage_not_persist(client, operator_a_headers, opportunity_a):
    """Suggest triage does NOT persist the suggestion."""
    with patch("app.services.agent.generate_agent_reply") as mock_agent:
        mock_agent.return_value = json.dumps({
            "action": "prepare_proposal",
            "reasoning": "Should not be persisted",
            "confidence": 0.9,
        })

        response = client.post(
            "/opportunities/1/suggest-triage",
            headers=operator_a_headers,
        )

    assert response.status_code == 200

    # Verify opportunity next_action is still "pending"
    get_opp = client.get(
        "/opportunities/1",
        headers=operator_a_headers,
    )
    assert get_opp.status_code == 200
    assert get_opp.json()["next_action"] == "pending"
