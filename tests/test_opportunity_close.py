"""Tests for WP-074: closing opportunities as done or lost.

The operator should be able to mark an opportunity as 'done' (won/completed)
or 'lost' (rejected/abandoned) to close the commercial cycle.
"""

from datetime import datetime, timezone

import pytest

from app.models import Company, Opportunity
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


@pytest.fixture
def opportunity_a(company_a):
    with TestingSessionLocal() as db:
        opp = Opportunity(
            company_id=1,
            source="intake",
            external_url="test:close-opportunity",
            title="Close opportunity test",
            description="Test opportunity for closing",
            captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            next_action="pending",
        )
        db.add(opp)
        db.commit()
        return opp.id


def test_triage_to_done(client, operator_a_headers, opportunity_a):
    """Operator can triage an opportunity to done."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={
            "next_action": "done",
            "triage_note": "Project completed successfully.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_action"] == "done"
    assert data["triage_note"] == "Project completed successfully."


def test_triage_to_lost(client, operator_a_headers, opportunity_a):
    """Operator can triage an opportunity to lost."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={
            "next_action": "lost",
            "triage_note": "Client chose a different vendor.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_action"] == "lost"
    assert data["triage_note"] == "Client chose a different vendor."


def test_triage_done_no_note(client, operator_a_headers, opportunity_a):
    """Triage to done works without a note."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "done"},
    )
    assert resp.status_code == 200
    assert resp.json()["next_action"] == "done"


def test_triage_lost_no_note(client, operator_a_headers, opportunity_a):
    """Triage to lost works without a note."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "lost"},
    )
    assert resp.status_code == 200
    assert resp.json()["next_action"] == "lost"


def test_done_blocks_proposal_brief(client, operator_a_headers, opportunity_a):
    """A done opportunity cannot create a proposal brief."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "done"},
    )
    resp = client.post(
        f"/opportunities/{opportunity_a}/proposal-brief",
        headers=operator_a_headers,
        json={
            "offer_reference": "Test",
            "diagnosis": "Test",
            "scope": "Test",
            "deliverables": "Test",
            "acceptance_criteria": "Test",
        },
    )
    assert resp.status_code == 409
    assert "not ready for proposal" in resp.json()["detail"].lower()


def test_lost_blocks_proposal_brief(client, operator_a_headers, opportunity_a):
    """A lost opportunity cannot create a proposal brief."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "lost"},
    )
    resp = client.post(
        f"/opportunities/{opportunity_a}/proposal-brief",
        headers=operator_a_headers,
        json={
            "offer_reference": "Test",
            "diagnosis": "Test",
            "scope": "Test",
            "deliverables": "Test",
            "acceptance_criteria": "Test",
        },
    )
    assert resp.status_code == 409
    assert "not ready for proposal" in resp.json()["detail"].lower()


def test_done_reflects_in_list(client, operator_a_headers, opportunity_a):
    """Opportunity triaged to done appears correctly in list."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "done"},
    )
    resp = client.get("/opportunities", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    found = [o for o in data if o["id"] == opportunity_a]
    assert len(found) == 1
    assert found[0]["next_action"] == "done"


def test_lost_reflects_in_list(client, operator_a_headers, opportunity_a):
    """Opportunity triaged to lost appears correctly in list."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "lost"},
    )
    resp = client.get("/opportunities", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    found = [o for o in data if o["id"] == opportunity_a]
    assert len(found) == 1
    assert found[0]["next_action"] == "lost"


def test_triage_done_requires_auth(client, opportunity_a):
    """Triage to done requires authentication."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        json={"next_action": "done"},
    )
    assert resp.status_code == 401


def test_triage_lost_tenant_isolation(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Triage to lost respects tenant isolation."""
    from tests.test_api import create_company, create_opportunity

    create_company(client, admin_headers, name="Company A", slug="company-a")
    create_company(client, admin_headers, name="Company B", slug="company-b")
    opp_b = create_opportunity(
        client,
        operator_b_headers,
        external_url="https://example.invalid/cross-tenant-lost",
        title="Cross tenant lost test",
    )
    # Operator A cannot triage Company B's opportunity to lost
    resp = client.patch(
        f"/opportunities/{opp_b['id']}/triage",
        headers=operator_a_headers,
        json={"next_action": "lost"},
    )
    assert resp.status_code == 404
