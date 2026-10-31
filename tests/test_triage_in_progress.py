"""Tests for WP-073: in_progress as a manual triage option.

The operator should be able to mark an opportunity as 'in_progress'
without going through the proposal brief approval flow.
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
            external_url="test:in-progress-triage",
            title="In progress triage test",
            description="Test opportunity",
            captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            next_action="pending",
        )
        db.add(opp)
        db.commit()
        return opp.id


def test_triage_to_in_progress(client, operator_a_headers, opportunity_a):
    """Operator can triage an opportunity to in_progress."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={
            "next_action": "in_progress",
            "triage_note": "Started working on this directly.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_action"] == "in_progress"
    assert data["triage_note"] == "Started working on this directly."


def test_triage_in_progress_no_triage_note(client, operator_a_headers, opportunity_a):
    """Triage to in_progress works without a triage note."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={
            "next_action": "in_progress",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["next_action"] == "in_progress"


def test_triage_in_progress_blocks_proposal_brief(
    client, operator_a_headers, opportunity_a
):
    """An in_progress opportunity cannot create a proposal brief."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "in_progress"},
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


def test_triage_in_progress_tenant_isolation(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Triage to in_progress respects tenant isolation."""
    from tests.test_api import create_company, create_opportunity

    create_company(client, admin_headers, name="Company A", slug="company-a")
    create_company(client, admin_headers, name="Company B", slug="company-b")
    opp_b = create_opportunity(
        client,
        operator_b_headers,
        external_url="https://example.invalid/cross-tenant-in-progress",
        title="Cross tenant test",
    )
    # Operator A cannot triage Company B's opportunity
    resp = client.patch(
        f"/opportunities/{opp_b['id']}/triage",
        headers=operator_a_headers,
        json={"next_action": "in_progress"},
    )
    assert resp.status_code == 404


def test_triage_in_progress_requires_auth(client, opportunity_a):
    """Triage to in_progress requires authentication."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        json={"next_action": "in_progress"},
    )
    assert resp.status_code == 401


def test_triage_in_progress_invalid_action(client, operator_a_headers, opportunity_a):
    """Invalid next_action is rejected."""
    resp = client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "invalid_action"},
    )
    assert resp.status_code == 422


def test_triage_in_progress_reflects_in_list(client, operator_a_headers, opportunity_a):
    """Opportunity triaged to in_progress appears correctly in list."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "in_progress"},
    )
    resp = client.get("/opportunities", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    found = [o for o in data if o["id"] == opportunity_a]
    assert len(found) == 1
    assert found[0]["next_action"] == "in_progress"


def test_triage_in_progress_filter(client, operator_a_headers, opportunity_a):
    """Opportunity triaged to in_progress appears in filtered list."""
    client.patch(
        f"/opportunities/{opportunity_a}/triage",
        headers=operator_a_headers,
        json={"next_action": "in_progress"},
    )
    resp = client.get(
        "/opportunities?next_action=in_progress",
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["next_action"] == "in_progress"
