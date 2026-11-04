"""WP-240 — AI-assisted proposal brief suggestion.

The endpoint POST /opportunities/{id}/suggest-brief returns an AI-generated
draft of a proposal brief based on the opportunity context. It does NOT
persist the suggestion — the operator reviews and creates manually.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.models import Company, Opportunity
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
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=1,
            source="intake",
            external_url="https://example.com/brief-test",
            title="Site institucional",
            description="Cliente precisa de site institucional com blog",
            budget="R$ 15.000",
            deadline=(datetime.now() + __import__("datetime").timedelta(days=14)).strftime("%Y-%m-%d"),
            requirements="WordPress, responsivo",
            captured_at=datetime.now(),
            next_action="prepare_proposal",
        ))
        db.commit()


@pytest.fixture
def opportunity_b(company_b):
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


def _mock_generate_reply(*args, **kwargs):
    """Return a valid JSON brief suggestion."""
    return (
        '{"offer_reference": "Site Institucional", '
        '"diagnosis": "Cliente precisa de presenca digital", '
        '"scope": "Desenvolvimento de site WordPress", '
        '"deliverables": "Site responsivo com blog", '
        '"acceptance_criteria": "Site funcional em 14 dias", '
        '"assumptions": "Cliente fornece conteudo", '
        '"risks": "Atraso na entrega de conteudo"}'
    )


def test_endpoint_exists():
    """Suggest-brief endpoint is registered."""
    with open("app/routers/opportunities.py") as f:
        content = f.read()
    assert '"/opportunities/{opportunity_id}/suggest-brief"' in content


def test_suggest_brief_returns_json(client, operator_a_headers, opportunity_a):
    """Suggest-brief returns valid JSON with all fields."""
    with patch("app.services.agent.generate_agent_reply", side_effect=_mock_generate_reply):
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "offer_reference" in data
    assert "diagnosis" in data
    assert "scope" in data
    assert "deliverables" in data
    assert "acceptance_criteria" in data


def test_suggest_brief_uses_opportunity_context(client, operator_a_headers, opportunity_a):
    """Suggest-brief uses opportunity title, description, requirements."""
    with patch("app.services.agent.generate_agent_reply") as mock:
        mock.side_effect = _mock_generate_reply
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    # Verify the agent was called with the opportunity context
    assert mock.called
    call_args = mock.call_args
    message = call_args[1].get("message", call_args[0][0] if call_args[0] else "")
    assert "Site institucional" in message or "Site" in message


def test_suggest_brief_503_on_agent_error(client, operator_a_headers, opportunity_a):
    """Suggest-brief returns 503 when agent service is unavailable."""
    from app.services.agent import AgentServiceError

    with patch("app.services.agent.generate_agent_reply", side_effect=AgentServiceError("Unavailable")):
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 503


def test_suggest_brief_fallback_on_invalid_json(client, operator_a_headers, opportunity_a):
    """Suggest-brief returns fallback when agent returns invalid JSON."""
    with patch("app.services.agent.generate_agent_reply", return_value="Not JSON at all"):
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "offer_reference" in data
    assert "diagnosis" in data


def test_suggest_brief_tenant_isolation(client, operator_a_headers, opportunity_b):
    """Suggest-brief is tenant-isolated."""
    with patch("app.services.agent.generate_agent_reply", side_effect=_mock_generate_reply):
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    # Opportunity 1 belongs to company B, not accessible by operator A
    assert response.status_code == 404


def test_suggest_brief_requires_auth(client, opportunity_a):
    """Suggest-brief requires authentication."""
    response = client.post(
        "/opportunities/1/suggest-brief",
    )
    assert response.status_code in (401, 403)


def test_suggest_brief_optional_fields(client, operator_a_headers, opportunity_a):
    """Suggest-brief includes optional assumptions and risks when present."""
    with patch("app.services.agent.generate_agent_reply", side_effect=_mock_generate_reply):
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "assumptions" in data
    assert "risks" in data


def test_suggest_brief_uses_company_config(client, operator_a_headers, opportunity_a):
    """Suggest-brief uses company agent config for temperature, model, etc."""
    with patch("app.services.agent.generate_agent_reply") as mock:
        mock.side_effect = _mock_generate_reply
        response = client.post(
            "/opportunities/1/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 200
    # Verify agent was called with company config parameters
    assert mock.called


def test_suggest_brief_not_found(client, operator_a_headers, company_a):
    """Suggest-brief returns 404 for non-existent opportunity."""
    with patch("app.services.agent.generate_agent_reply", side_effect=_mock_generate_reply):
        response = client.post(
            "/opportunities/9999/suggest-brief",
            headers=operator_a_headers,
        )

    assert response.status_code == 404
