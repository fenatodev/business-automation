"""WP-244 — Brief metrics in dashboard.

The dashboard endpoint now includes briefs_by_status, showing proposal
brief counts grouped by status (draft, ready_for_review, approved, rejected),
tenant-isolated via JOIN with Opportunity.
"""

from datetime import datetime

import pytest

from app.models import Company, Opportunity, ProposalBrief
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
def briefs_a(company_a):
    """Create briefs with different statuses in company A."""
    with TestingSessionLocal() as db:
        opp1 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/1",
            title="Site A", description="Test", captured_at=datetime.now(),
        )
        opp2 = Opportunity(
            company_id=1, source="intake", external_url="https://example.com/2",
            title="App B", description="Test", captured_at=datetime.now(),
        )
        opp3 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/3",
            title="API C", description="Test", captured_at=datetime.now(),
        )
        db.add_all([opp1, opp2, opp3])
        db.flush()

        db.add(ProposalBrief(
            opportunity_id=opp1.id, offer_reference="site-a",
            diagnosis="Problema X", scope="Escopo A",
            deliverables="Entregável 1", acceptance_criteria="Critério 1",
            status="draft",
        ))
        db.add(ProposalBrief(
            opportunity_id=opp2.id, offer_reference="app-b",
            diagnosis="Problema Y", scope="Escopo B",
            deliverables="Entregável 2", acceptance_criteria="Critério 2",
            status="ready_for_review",
        ))
        db.add(ProposalBrief(
            opportunity_id=opp3.id, offer_reference="api-c",
            diagnosis="Problema Z", scope="Escopo C",
            deliverables="Entregável 3", acceptance_criteria="Critério 3",
            status="approved",
        ))
        db.commit()


@pytest.fixture
def brief_b(company_b):
    """Create a brief in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        opp = Opportunity(
            company_id=2, source="manual", external_url="https://example.com/other",
            title="Other tenant", description="Test", captured_at=datetime.now(),
        )
        db.add(opp)
        db.flush()
        db.add(ProposalBrief(
            opportunity_id=opp.id, offer_reference="other",
            diagnosis="Other", scope="Other", deliverables="Other",
            acceptance_criteria="Other", status="draft",
        ))
        db.commit()


def test_dashboard_includes_briefs_key(client, operator_a_headers, briefs_a):
    """Dashboard response includes briefs key."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "briefs" in data


def test_dashboard_briefs_counts_by_status(client, operator_a_headers, briefs_a):
    """Brief counts are grouped by status."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    briefs = data["briefs"]
    assert briefs["total"] == 3
    assert briefs["draft"] == 1
    assert briefs["ready_for_review"] == 1
    assert briefs["approved"] == 1


def test_dashboard_briefs_tenant_isolation(client, operator_a_headers, brief_b):
    """Briefs are tenant-isolated — company A sees no briefs."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    briefs = data["briefs"]
    assert briefs["total"] == 0


def test_dashboard_briefs_empty_when_none(client, operator_a_headers, company_a):
    """Dashboard returns empty briefs when no briefs exist."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    briefs = data["briefs"]
    assert briefs["total"] == 0


def test_dashboard_briefs_requires_auth(client, briefs_a):
    """Dashboard briefs require authentication."""
    response = client.get("/internal-tasks/dashboard")
    assert response.status_code in (401, 403)
