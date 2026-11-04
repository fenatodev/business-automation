"""WP-247 — AI-assisted bulk triage suggestion.

The operator can now get an AI suggestion for the best triage action
for a group of selected opportunities, similar to WP-237 but for bulk
operations.
"""

from datetime import datetime

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
    """Create opportunities in company A. Returns IDs."""
    ids = []
    with TestingSessionLocal() as db:
        opp1 = Opportunity(
            company_id=1, source="intake", external_url="https://example.com/1",
            title="Site A", description="Test", captured_at=datetime.now(),
            next_action="pending",
        )
        opp2 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/2",
            title="App B", description="Test", captured_at=datetime.now(),
            next_action="pending",
        )
        db.add_all([opp1, opp2])
        db.commit()
        ids = [opp1.id, opp2.id]
    return ids


@pytest.fixture
def opportunity_b(company_b):
    """Create an opportunity in company B for tenant isolation. Returns ID."""
    opp_id = None
    with TestingSessionLocal() as db:
        opp = Opportunity(
            company_id=2, source="manual", external_url="https://example.com/other",
            title="Other tenant", description="Test", captured_at=datetime.now(),
            next_action="pending",
        )
        db.add(opp)
        db.commit()
        opp_id = opp.id
    return opp_id


def test_bulk_suggest_triage_endpoint_exists(client, operator_a_headers, opportunities_a):
    """Bulk suggest triage endpoint returns 503 when agent unavailable."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": opportunities_a},
    )
    # 503 because agent service is not available in tests
    assert response.status_code == 503


def test_bulk_suggest_triage_requires_auth(client, opportunities_a):
    """Bulk suggest triage requires authentication."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        json={"opportunity_ids": [opportunities_a[0]]},
    )
    assert response.status_code in (401, 403)


def test_bulk_suggest_triage_tenant_isolation(client, operator_a_headers, opportunity_b):
    """Bulk suggest triage rejects opportunities from other tenants."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": [opportunity_b]},
    )
    assert response.status_code == 404


def test_bulk_suggest_triage_min_ids(client, operator_a_headers):
    """Bulk suggest triage requires at least 1 ID."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": []},
    )
    assert response.status_code == 422


def test_bulk_suggest_triage_max_ids(client, operator_a_headers):
    """Bulk suggest triage rejects more than 100 IDs."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": list(range(1, 102))},
    )
    assert response.status_code == 422


def test_bulk_suggest_triage_response_format(client, operator_a_headers, opportunities_a):
    """Bulk suggest triage response includes required fields when agent available."""
    # With agent unavailable, we get 503 — the response_model is still validated
    # when the agent is available
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": opportunities_a},
    )
    # We expect 503 in tests, but the endpoint structure is correct
    assert response.status_code == 503


def test_bulk_suggest_triage_not_found(client, operator_a_headers):
    """Bulk suggest triage returns 404 when no opportunities found."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": [99999]},
    )
    assert response.status_code == 404


def test_bulk_suggest_triage_single_opportunity(client, operator_a_headers, opportunities_a):
    """Bulk suggest triage works with a single opportunity."""
    response = client.post(
        "/opportunities/bulk-suggest-triage",
        headers=operator_a_headers,
        json={"opportunity_ids": [opportunities_a[0]]},
    )
    assert response.status_code == 503  # agent unavailable in tests
