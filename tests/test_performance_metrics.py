"""WP-256 — Business performance metrics in dashboard.

The dashboard endpoint now includes performance_metrics with:
- lead_conversion_rate: % of leads converted to customers
- opportunity_closure_rate: % of opportunities closed (done/lost/ignore)
- brief_approval_rate: % of briefs approved
"""

from datetime import datetime

import pytest

from app.models import Company, Lead, Opportunity, ProposalBrief
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


def test_performance_metrics_empty_tenant(client, operator_a_headers, company_a):
    """Empty tenant returns zero rates."""
    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["performance_metrics"]
    assert metrics["lead_conversion_rate"] == 0.0
    assert metrics["opportunity_closure_rate"] == 0.0
    assert metrics["brief_approval_rate"] == 0.0
    assert metrics["lead_conversion_count"] == "0/0"
    assert metrics["opportunity_closure_count"] == "0/0"
    assert metrics["brief_approval_count"] == "0/0"


def test_lead_conversion_rate(client, operator_a_headers, company_a):
    """Lead conversion rate reflects converted leads."""
    with TestingSessionLocal() as db:
        db.add(Lead(company_id=1, name="Lead 1", phone="111", source="website", status="new"))
        db.add(Lead(company_id=1, name="Lead 2", phone="222", source="website", status="converted"))
        db.add(Lead(company_id=1, name="Lead 3", phone="333", source="website", status="qualified"))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["performance_metrics"]
    # 1 converted out of 3 total = 33.3%
    assert metrics["lead_conversion_rate"] == 33.3
    assert metrics["lead_conversion_count"] == "1/3"


def test_opportunity_closure_rate(client, operator_a_headers, company_a):
    """Opportunity closure rate reflects closed opportunities."""
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=1, source="manual", external_url="https://example.com/1",
            title="Opp 1", description="Test", captured_at=datetime.now(),
            next_action="pending",
        ))
        db.add(Opportunity(
            company_id=1, source="manual", external_url="https://example.com/2",
            title="Opp 2", description="Test", captured_at=datetime.now(),
            next_action="done",
        ))
        db.add(Opportunity(
            company_id=1, source="manual", external_url="https://example.com/3",
            title="Opp 3", description="Test", captured_at=datetime.now(),
            next_action="lost",
        ))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["performance_metrics"]
    # 2 closed (done + lost) out of 3 = 66.7%
    assert metrics["opportunity_closure_rate"] == 66.7
    assert metrics["opportunity_closure_count"] == "2/3"


def test_brief_approval_rate(client, operator_a_headers, company_a):
    """Brief approval rate reflects approved briefs."""
    with TestingSessionLocal() as db:
        opp1 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/b1",
            title="Brief Opp 1", description="Test", captured_at=datetime.now(),
            next_action="proposal",
        )
        db.add(opp1)
        db.flush()

        opp2 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/b2",
            title="Brief Opp 2", description="Test", captured_at=datetime.now(),
            next_action="proposal",
        )
        db.add(opp2)
        db.flush()

        opp3 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/b3",
            title="Brief Opp 3", description="Test", captured_at=datetime.now(),
            next_action="proposal",
        )
        db.add(opp3)
        db.flush()

        db.add(ProposalBrief(opportunity_id=opp1.id, offer_reference="REF-1", diagnosis="D", scope="S", deliverables="E", acceptance_criteria="C", status="approved"))
        db.add(ProposalBrief(opportunity_id=opp2.id, offer_reference="REF-2", diagnosis="D", scope="S", deliverables="E", acceptance_criteria="C", status="draft"))
        db.add(ProposalBrief(opportunity_id=opp3.id, offer_reference="REF-3", diagnosis="D", scope="S", deliverables="E", acceptance_criteria="C", status="rejected"))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["performance_metrics"]
    # 1 approved out of 3 = 33.3%
    assert metrics["brief_approval_rate"] == 33.3
    assert metrics["brief_approval_count"] == "1/3"


def test_performance_metrics_tenant_isolation(client, operator_a_headers, company_a, company_b):
    """Performance metrics are tenant-isolated."""
    with TestingSessionLocal() as db:
        # Company A: 2 leads, 1 converted
        db.add(Lead(company_id=1, name="A Lead 1", phone="111", source="website", status="new"))
        db.add(Lead(company_id=1, name="A Lead 2", phone="222", source="website", status="converted"))
        # Company B: 1 lead, 0 converted
        db.add(Lead(company_id=2, name="B Lead 1", phone="333", source="website", status="new"))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["performance_metrics"]
    # Company A: 1/2 = 50.0%
    assert metrics["lead_conversion_rate"] == 50.0
    assert metrics["lead_conversion_count"] == "1/2"


def test_performance_metrics_requires_auth(client, company_a):
    """Dashboard requires authentication."""
    response = client.get("/internal-tasks/dashboard")
    assert response.status_code in (401, 403)


def test_ignore_counts_as_closed(client, operator_a_headers, company_a):
    """Opportunities with 'ignore' status count as closed."""
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=1, source="manual", external_url="https://example.com/ignore",
            title="Ignored", description="Test", captured_at=datetime.now(),
            next_action="ignore",
        ))
        db.commit()

    response = client.get(
        "/internal-tasks/dashboard",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    data = response.json()
    metrics = data["performance_metrics"]
    # 1 ignored out of 1 = 100.0%
    assert metrics["opportunity_closure_rate"] == 100.0
    assert metrics["opportunity_closure_count"] == "1/1"
