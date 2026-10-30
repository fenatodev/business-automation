"""Tests for proposal brief approval flow (WP-071)."""

from datetime import datetime, timezone

import pytest

from app.models import Company, Opportunity, ProposalBrief
from conftest import TestingSessionLocal, OPERATOR_A_TOKEN, OPERATOR_B_TOKEN


def _op_a_headers():
    return {"Authorization": f"Bearer {OPERATOR_A_TOKEN}"}


def _op_b_headers():
    return {"Authorization": f"Bearer {OPERATOR_B_TOKEN}"}


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
        opp = Opportunity(
            company_id=1,
            source="intake",
            external_url="intake:test-001",
            title="Test opportunity",
            description="Test description",
            captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            next_action="prepare_proposal",
        )
        db.add(opp)
        db.commit()
        db.refresh(opp)
        return opp.id


@pytest.fixture
def brief_draft(opportunity_a):
    with TestingSessionLocal() as db:
        brief = ProposalBrief(
            opportunity_id=opportunity_a,
            offer_reference="test-offer",
            diagnosis="Test diagnosis",
            scope="Test scope",
            deliverables="Test deliverables",
            acceptance_criteria="Test criteria",
            status="draft",
        )
        db.add(brief)
        db.commit()
        db.refresh(brief)
        return brief.id


@pytest.fixture
def brief_ready(opportunity_a):
    with TestingSessionLocal() as db:
        brief = ProposalBrief(
            opportunity_id=opportunity_a,
            offer_reference="test-offer",
            diagnosis="Test diagnosis",
            scope="Test scope",
            deliverables="Test deliverables",
            acceptance_criteria="Test criteria",
            status="ready_for_review",
        )
        db.add(brief)
        db.commit()
        db.refresh(brief)
        return brief.id


def test_approve_ready_brief_succeeds(client, company_a, opportunity_a, brief_ready):
    """Approving a ready_for_review brief succeeds."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/proposal-brief/approve",
        headers=_op_a_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"

    # Verify opportunity advanced
    with TestingSessionLocal() as db:
        opp = db.get(Opportunity, opportunity_a)
        assert opp.next_action == "in_progress"


def test_approve_draft_brief_returns_400(client, company_a, opportunity_a, brief_draft):
    """Cannot approve a draft brief."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/proposal-brief/approve",
        headers=_op_a_headers(),
    )
    assert resp.status_code == 400
    assert "ready_for_review" in resp.json()["detail"].lower()


def test_approve_already_approved_returns_400(client, company_a, opportunity_a, brief_ready):
    """Cannot approve an already approved brief twice."""
    # First approval
    client.patch(
        f"/opportunities/{opportunity_a}/proposal-brief/approve",
        headers=_op_a_headers(),
    )
    # Second approval should fail
    resp = client.patch(
        f"/opportunities/{opportunity_a}/proposal-brief/approve",
        headers=_op_a_headers(),
    )
    assert resp.status_code == 400


def test_approve_without_auth_returns_401(client, company_a, opportunity_a, brief_ready):
    """Unauthenticated approval returns 401."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/proposal-brief/approve",
    )
    assert resp.status_code == 401


def test_approve_wrong_tenant_returns_404(client, company_a, company_b, brief_ready):
    """Operator from different company cannot approve."""
    resp = client.patch(
        f"/opportunities/{brief_ready}/proposal-brief/approve",
        headers=_op_b_headers(),
    )
    # company_b (id=2) cannot access company_a's opportunity
    assert resp.status_code in (404, 403)


def test_approve_nonexistent_opportunity_returns_404(client, company_a):
    """Approving a non-existent opportunity returns 404."""
    resp = client.patch(
        "/opportunities/99999/proposal-brief/approve",
        headers=_op_a_headers(),
    )
    assert resp.status_code == 404


def test_approve_atomic_update(client, company_a, opportunity_a, brief_ready):
    """Approval updates both brief and opportunity atomically."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/proposal-brief/approve",
        headers=_op_a_headers(),
    )
    assert resp.status_code == 200

    with TestingSessionLocal() as db:
        brief = db.get(ProposalBrief, brief_ready)
        opp = db.get(Opportunity, opportunity_a)
        assert brief.status == "approved"
        assert opp.next_action == "in_progress"
