"""WP-239 — High priority opportunities in dashboard.

The dashboard endpoint now includes high_priority_opportunities,
showing the top 5 opportunities with priority level "high" sorted
by score descending.
"""

from datetime import datetime, timedelta

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
def opportunities_a(company_a):
    """Create opportunities with different priority levels in company A."""
    now = datetime.now()
    with TestingSessionLocal() as db:
        # High priority: pending, close deadline, budget, intake source
        db.add(Opportunity(
            company_id=1,
            source="intake",
            external_url="https://example.com/high1",
            title="Site urgente",
            description="Precisa agora",
            budget="R$ 50.000",
            deadline=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
            requirements="WordPress",
            captured_at=now,
            next_action="pending",
        ))
        # Another high priority: expired deadline
        db.add(Opportunity(
            company_id=1,
            source="review_queue",
            external_url="https://example.com/high2",
            title="Prazo expirado",
            description="Deveria estar pronto",
            budget="R$ 30.000",
            deadline=(now - timedelta(days=5)).strftime("%Y-%m-%d"),
            requirements="Urgente",
            captured_at=now,
            next_action="pending",
        ))
        # Medium priority: follow, medium deadline, no budget
        db.add(Opportunity(
            company_id=1,
            source="manual",
            external_url="https://example.com/medium",
            title="Projeto médio",
            description="Pode esperar",
            budget=None,
            deadline=(now + timedelta(days=20)).strftime("%Y-%m-%d"),
            requirements="",
            captured_at=now,
            next_action="follow",
        ))
        # Low priority: done, far deadline
        db.add(Opportunity(
            company_id=1,
            source="import",
            external_url="https://example.com/low",
            title="Projeto antigo",
            description="Já concluído",
            budget=None,
            deadline=(now + timedelta(days=90)).strftime("%Y-%m-%d"),
            requirements="",
            captured_at=now,
            next_action="done",
        ))
        db.commit()


@pytest.fixture
def opportunity_b(company_b):
    """Create a high-priority opportunity in company B for tenant isolation."""
    now = datetime.now()
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=2,
            source="intake",
            external_url="https://example.com/other-tenant",
            title="Other tenant urgent",
            description="Should not be accessible",
            budget="R$ 100.000",
            deadline=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
            captured_at=now,
            next_action="pending",
        ))
        db.commit()


def test_dashboard_includes_high_priority_key(client, operator_a_headers, opportunities_a):
    """Dashboard response includes high_priority_opportunities key."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "high_priority_opportunities" in data


def test_dashboard_high_priority_returns_high_level_only(client, operator_a_headers, opportunities_a):
    """Only high-priority opportunities appear in the dashboard section."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    high_priority = data["high_priority_opportunities"]

    # Should have 2 high-priority opportunities (Site urgente + Prazo expirado)
    assert len(high_priority) == 2
    for item in high_priority:
        assert item["priority_level"] == "high"


def test_dashboard_high_priority_ordered_by_score(client, operator_a_headers, opportunities_a):
    """High priority opportunities are ordered by score descending."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    high_priority = data["high_priority_opportunities"]

    scores = [item["priority_score"] for item in high_priority]
    assert scores == sorted(scores, reverse=True)


def test_dashboard_high_priority_includes_fields(client, operator_a_headers, opportunities_a):
    """Each high priority item includes required fields."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()

    for item in data["high_priority_opportunities"]:
        assert "id" in item
        assert "title" in item
        assert "priority_score" in item
        assert "priority_level" in item
        assert "next_action" in item


def test_dashboard_high_priority_limit_5(client, operator_a_headers, company_a):
    """Dashboard shows at most 5 high-priority opportunities."""
    now = datetime.now()
    with TestingSessionLocal() as db:
        # Create 10 high-priority opportunities
        for i in range(10):
            db.add(Opportunity(
                company_id=1,
                source="intake",
                external_url=f"https://example.com/high-{i}",
                title=f"Urgente {i}",
                description="Test",
                budget="R$ 10.000",
                deadline=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
                captured_at=now,
                next_action="pending",
            ))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["high_priority_opportunities"]) <= 5


def test_dashboard_high_priority_tenant_isolation(client, operator_a_headers, opportunity_b):
    """High priority opportunities are tenant-isolated."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Company A has no opportunities in this test
    high_priority = data["high_priority_opportunities"]
    assert len(high_priority) == 0


def test_dashboard_high_priority_empty_when_no_high(client, operator_a_headers, company_a):
    """Dashboard returns empty list when no high-priority opportunities exist."""
    now = datetime.now()
    with TestingSessionLocal() as db:
        # Only low-priority opportunity
        db.add(Opportunity(
            company_id=1,
            source="import",
            external_url="https://example.com/low",
            title="Projeto antigo",
            description="Já concluído",
            budget=None,
            deadline=(now + timedelta(days=90)).strftime("%Y-%m-%d"),
            captured_at=now,
            next_action="done",
        ))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["high_priority_opportunities"] == []


def test_dashboard_high_priority_requires_auth(client, opportunities_a):
    """Dashboard high priority requires authentication."""
    response = client.get(
        "/internal-tasks/dashboard",
    )
    assert response.status_code in (401, 403)
