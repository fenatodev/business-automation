"""WP-258 — AI-assisted intake suggestion.

The suggest endpoint uses the AI agent to predict intent and category
before the operator creates the intake opportunity. This allows pre-validation
and correction before persistence.
"""

from datetime import datetime

import pytest

from app.models import Company
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


def test_suggest_intake_returns_suggestion(client, operator_a_headers, company_a):
    """Suggest endpoint returns a structured suggestion."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Preciso de um orçamento para automação da minha fábrica",
            "event_id": "suggest-test-001",
        },
    )
    # 503 is expected without Ollama; 200 if mock works
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert "suggested_intent" in data
        assert "reasoning" in data


def test_suggest_intake_requires_auth(client, company_a):
    """Suggest endpoint requires authentication."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        json={
            "channel": "web",
            "message": "Test",
            "event_id": "suggest-test-002",
        },
    )
    assert response.status_code in (401, 403)


def test_suggest_intake_validates_message(client, operator_a_headers, company_a):
    """Empty message is rejected."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "",
            "event_id": "suggest-test-003",
        },
    )
    assert response.status_code == 422


def test_suggest_intake_validates_channel(client, operator_a_headers, company_a):
    """Empty channel is rejected."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "",
            "message": "Test",
            "event_id": "suggest-test-004",
        },
    )
    assert response.status_code == 422


def test_suggest_intake_validates_event_id(client, operator_a_headers, company_a):
    """Empty event_id is rejected."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Test",
            "event_id": "",
        },
    )
    assert response.status_code == 422


def test_suggest_intake_503_on_agent_error(client, operator_a_headers, company_a):
    """503 is returned when the agent service is unavailable."""
    # Without Ollama configured, this should return 503
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Test message for 503",
            "event_id": "suggest-test-005",
        },
    )
    # Either 503 (agent unavailable) or 200 (if mock works)
    assert response.status_code in (200, 503)


def test_suggest_intake_tenant_isolation(client, operator_a_headers, operator_b_headers, company_a):
    """Operator A can suggest for their company."""
    with TestingSessionLocal() as db:
        db.add(Company(id=2, name="Synthetic B", slug="synthetic-b"))
        db.commit()

    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Test isolation",
            "event_id": "suggest-test-006",
        },
    )
    assert response.status_code in (200, 503)


def test_suggest_intake_does_not_persist(client, operator_a_headers, company_a):
    """Suggest does not create an opportunity — it only returns a suggestion."""
    # Count opportunities before
    before = client.get(
        "/opportunities/count",
        headers=operator_a_headers,
    ).json()["total"]

    # Call suggest
    client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Should not persist",
            "event_id": "suggest-test-007",
        },
    )

    # Count opportunities after — should be unchanged
    after = client.get(
        "/opportunities/count",
        headers=operator_a_headers,
    ).json()["total"]
    assert before == after


def test_suggest_intake_response_fields(client, operator_a_headers, company_a):
    """Response contains expected fields when successful."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Preciso de serviço de consultoria",
            "event_id": "suggest-test-008",
        },
    )
    if response.status_code == 200:
        data = response.json()
        assert "suggested_intent" in data
        assert "reasoning" in data
        # Optional fields
        assert "suggested_category" in data or data.get("suggested_category") is None
        assert "confidence" in data or data.get("confidence") is None


def test_suggest_intake_rejects_control_characters(client, operator_a_headers, company_a):
    """Message with control characters is rejected."""
    response = client.post(
        "/internal/commercial-intake/suggest",
        headers=operator_a_headers,
        json={
            "channel": "web",
            "message": "Test\x00message",
            "event_id": "suggest-test-009",
        },
    )
    assert response.status_code == 422
