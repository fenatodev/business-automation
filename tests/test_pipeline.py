"""Tests for opportunity pipeline filter and summary (WP-072)."""

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
def company_b():
    with TestingSessionLocal() as db:
        db.add(Company(id=2, name="Synthetic B", slug="synthetic-b"))
        db.commit()


@pytest.fixture
def opportunities_a(company_a):
    """Create opportunities with different next_action values in company A."""
    with TestingSessionLocal() as db:
        opps = []
        for title, action in [
            ("Pending task", "pending"),
            ("Follow up", "follow"),
            ("Prepare proposal", "prepare_proposal"),
            ("In progress", "in_progress"),
            ("Ignored item", "ignore"),
            ("Another pending", "pending"),
        ]:
            opp = Opportunity(
                company_id=1,
                source="intake",
                external_url=f"test:{title.lower().replace(' ', '-')}",
                title=title,
                description="Test",
                captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                next_action=action,
            )
            db.add(opp)
            opps.append(opp)
        db.commit()
        return [o.id for o in opps]


@pytest.fixture
def opportunities_b(company_b):
    """Create opportunities in company B for tenant isolation tests."""
    with TestingSessionLocal() as db:
        for title, action in [
            ("Company B pending", "pending"),
            ("Company B follow", "follow"),
        ]:
            opp = Opportunity(
                company_id=2,
                source="intake",
                external_url=f"test-b:{title.lower().replace(' ', '-')}",
                title=title,
                description="Test",
                captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                next_action=action,
            )
            db.add(opp)
        db.commit()


# --- List filter tests ---


def test_list_all_without_filter(client, operator_a_headers, opportunities_a):
    """Without filter, returns all opportunities for the tenant."""
    resp = client.get("/opportunities", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 6


def test_list_filter_by_pending(client, operator_a_headers, opportunities_a):
    """Filter by next_action=pending returns only pending opportunities."""
    resp = client.get("/opportunities?next_action=pending", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for item in data:
        assert item["next_action"] == "pending"


def test_list_filter_by_single_item(client, operator_a_headers, opportunities_a):
    """Filter by next_action=in_progress returns only that one opportunity."""
    resp = client.get("/opportunities?next_action=in_progress", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["next_action"] == "in_progress"


def test_list_filter_by_ignore(client, operator_a_headers, opportunities_a):
    """Filter by next_action=ignore returns only ignored opportunities."""
    resp = client.get("/opportunities?next_action=ignore", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["next_action"] == "ignore"


def test_list_filter_no_match(client, operator_a_headers, opportunities_a):
    """Filter by a next_action with no matching opportunities returns empty list."""
    resp = client.get("/opportunities?next_action=nonexistent", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


# --- Tenant isolation tests ---


def test_list_filter_tenant_isolation(client, operator_a_headers, opportunities_a, opportunities_b):
    """Filter only returns opportunities from the authenticated tenant."""
    resp = client.get("/opportunities?next_action=pending", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for item in data:
        assert item["company_id"] == 1


def test_list_unauthorized(client, opportunities_a):
    """List without auth returns 401."""
    resp = client.get("/opportunities")
    assert resp.status_code == 401


# --- Pipeline summary tests ---


def test_pipeline_summary_returns_counts(client, operator_a_headers, opportunities_a):
    """Pipeline summary returns correct counts by next_action."""
    resp = client.get("/opportunities/pipeline-summary", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data["pending"] == 2
    assert data["follow"] == 1
    assert data["prepare_proposal"] == 1
    assert data["in_progress"] == 1
    assert data["ignore"] == 1


def test_pipeline_summary_tenant_isolation(client, operator_a_headers, opportunities_a, opportunities_b):
    """Pipeline summary only counts opportunities from the authenticated tenant."""
    resp = client.get("/opportunities/pipeline-summary", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] == 2


def test_pipeline_summary_empty(client, operator_a_headers, company_a):
    """Pipeline summary returns empty dict when no opportunities exist."""
    resp = client.get("/opportunities/pipeline-summary", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) == 0


def test_pipeline_summary_unauthorized(client, opportunities_a):
    """Pipeline summary without auth returns 401."""
    resp = client.get("/opportunities/pipeline-summary")
    assert resp.status_code == 401


def test_pipeline_summary_cross_tenant(client, operator_b_headers, opportunities_a, opportunities_b):
    """Operator B sees only company B's pipeline summary."""
    resp = client.get("/opportunities/pipeline-summary", headers=operator_b_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] == 1
    assert data["follow"] == 1
    assert "prepare_proposal" not in data or data["prepare_proposal"] == 0
