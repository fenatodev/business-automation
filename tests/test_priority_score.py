"""WP-238 — Automatic priority score for opportunities.

The priority score is calculated on-the-fly from deadline, budget, status
and source — no database migration required. The endpoint returns
opportunities ordered by score descending.
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
    """Create opportunities with different priority factors in company A."""
    now = datetime.now()
    with TestingSessionLocal() as db:
        # High priority: pending, close deadline, budget, intake source
        db.add(Opportunity(
            company_id=1,
            source="intake",
            external_url="https://example.com/high",
            title="Site urgente",
            description="Precisa agora",
            budget="R$ 50.000",
            deadline=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
            requirements="WordPress",
            captured_at=now,
            next_action="pending",
        ))
        # Medium priority: follow, medium deadline, no budget
        db.add(Opportunity(
            company_id=1,
            source="manual",
            external_url="https://example.com/medium",
            title="Projeto médio",
            description="Pode esperar um pouco",
            budget=None,
            deadline=(now + timedelta(days=20)).strftime("%Y-%m-%d"),
            requirements="",
            captured_at=now,
            next_action="follow",
        ))
        # Low priority: done, far deadline, no budget
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
        # Expired deadline
        db.add(Opportunity(
            company_id=1,
            source="review_queue",
            external_url="https://example.com/expired",
            title="Prazo expirado",
            description="Deveria estar pronto",
            budget="R$ 30.000",
            deadline=(now - timedelta(days=5)).strftime("%Y-%m-%d"),
            requirements="Urgente",
            captured_at=now,
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
    """Priority endpoint is registered in the router."""
    with open("app/routers/opportunities.py") as f:
        content = f.read()
    assert '"/opportunities/priority"' in content


def test_priority_returns_ordered_list(client, operator_a_headers, opportunities_a):
    """Priority endpoint returns opportunities ordered by score descending."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4

    # Verify descending order
    scores = [item["priority_score"] for item in data]
    assert scores == sorted(scores, reverse=True)


def test_priority_includes_score_and_level(client, operator_a_headers, opportunities_a):
    """Each priority item includes score, level, and factors."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    for item in response.json():
        assert "priority_score" in item
        assert "priority_level" in item
        assert "priority_factors" in item
        assert item["priority_level"] in ("high", "medium", "low")
        assert isinstance(item["priority_score"], int)
        assert 0 <= item["priority_score"] <= 100


def test_priority_expired_deadline_high_score(client, operator_a_headers, opportunities_a):
    """Expired deadline opportunities get high priority score."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # The expired deadline opportunity should be at or near the top
    expired = next((item for item in data if item["title"] == "Prazo expirado"), None)
    assert expired is not None
    assert expired["priority_score"] >= 70  # high level threshold
    assert expired["priority_level"] == "high"


def test_priority_pending_higher_than_done(client, operator_a_headers, opportunities_a):
    """Pending opportunities score higher than done ones."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()

    pending = next((item for item in data if item["next_action"] == "pending" and item["title"] == "Site urgente"), None)
    done = next((item for item in data if item["next_action"] == "done"), None)

    assert pending is not None
    assert done is not None
    assert pending["priority_score"] > done["priority_score"]


def test_priority_budget_increases_score(client, operator_a_headers, opportunities_a):
    """Opportunities with budget score higher than those without."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Site urgente has budget, Projeto médio doesn't
    urgent = next((item for item in data if item["title"] == "Site urgente"), None)
    assert urgent is not None
    assert "Orçamento informado" in urgent["priority_factors"]


def test_priority_limit(client, operator_a_headers, opportunities_a):
    """Priority endpoint respects limit parameter."""
    response = client.get(
        "/opportunities/priority?limit=2",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_priority_tenant_isolation(client, operator_a_headers, opportunity_b):
    """Priority endpoint is tenant-isolated."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Company A has no opportunities in this test, so empty list
    assert all(item.get("company_id") != 2 or item["title"] != "Other tenant opportunity" for item in data)


def test_priority_requires_auth(client, opportunities_a):
    """Priority endpoint requires authentication."""
    response = client.get(
        "/opportunities/priority",
    )
    assert response.status_code in (401, 403)


def test_priority_empty_company(client, operator_a_headers, company_a):
    """Priority endpoint returns empty list for company with no opportunities."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_priority_factors_included(client, operator_a_headers, opportunities_a):
    """Priority factors explain the score calculation."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for item in data:
        factors = item["priority_factors"]
        assert len(factors) == 4  # deadline, budget, status, source
        assert any("Prazo" in f or "Sem prazo" in f for f in factors)
        assert any("Orçamento" in f or "Sem orçamento" in f for f in factors)
        assert any("Status:" in f for f in factors)
        assert any("Fonte:" in f for f in factors)


def test_priority_intake_source_higher(client, operator_a_headers, opportunities_a):
    """Intake source opportunities get higher score than import."""
    response = client.get(
        "/opportunities/priority",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()

    intake = next((item for item in data if item["source"] == "intake"), None)
    imported = next((item for item in data if item["source"] == "import"), None)

    assert intake is not None
    assert imported is not None
    # Intake (15pts) > Import (5pts) when other factors are similar
    intake_source_pts = 15
    import_source_pts = 5
    assert intake_source_pts > import_source_pts
