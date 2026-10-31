"""WP-105 — Triagem em massa de oportunidades."""

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
    """Create opportunities in company A."""
    with TestingSessionLocal() as db:
        for i in range(5):
            db.add(Opportunity(
                company_id=1,
                source="intake",
                external_url=f"https://example.com/opp-a-{i}",
                title=f"Opportunity A {i}",
                description=f"Description A {i}",
                captured_at=datetime.now(),
                next_action="pending",
            ))
        db.commit()


@pytest.fixture
def opportunities_b(company_b):
    """Create opportunities in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        db.add(Opportunity(
            company_id=2,
            source="intake",
            external_url="https://example.com/opp-b-1",
            title="Secret Opportunity B",
            description="Should not be accessible",
            captured_at=datetime.now(),
            next_action="pending",
        ))
        db.commit()


# --- Basic bulk triage tests ---


def test_bulk_triage_basic(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 2, 3],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 3
    assert data["skipped"] == 0
    assert data["next_action"] == "follow"
    assert sorted(data["updated_ids"]) == [1, 2, 3]


def test_bulk_triage_with_note(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 2],
            "next_action": "prepare_proposal",
            "triage_note": "Prioridade alta",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2
    assert data["skipped"] == 0

    # Verify triage_note was set
    with TestingSessionLocal() as db:
        opp = db.get(Opportunity, 1)
        assert opp.next_action == "prepare_proposal"
        assert opp.triage_note == "Prioridade alta"


def test_bulk_triage_all_pending(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 2, 3, 4, 5],
            "next_action": "pending",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 5
    assert data["skipped"] == 0


def test_bulk_triage_ignore(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 2],
            "next_action": "ignore",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2


def test_bulk_triage_done(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1],
            "next_action": "done",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1


def test_bulk_triage_lost(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1],
            "next_action": "lost",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1


def test_bulk_triage_in_progress(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 2],
            "next_action": "in_progress",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2


# --- Skipped opportunities tests ---


def test_bulk_triage_skips_nonexistent(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 2, 9999],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2
    assert data["skipped"] == 1


def test_bulk_triage_skips_mixed(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 9998, 2, 9999],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2
    assert data["skipped"] == 2


# --- Tenant isolation tests ---


def test_bulk_triage_tenant_isolation(client, operator_a_headers, opportunities_a, opportunities_b):
    # Operator A tries to triage opportunity from company B (id=6)
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1, 6],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1
    assert data["skipped"] == 1
    assert 1 in data["updated_ids"]
    assert 6 not in data["updated_ids"]


def test_bulk_triage_cross_tenant_no_access(client, operator_a_headers, opportunities_b):
    # Operator A tries to triage only company B opportunities
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [6],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 0
    assert data["skipped"] == 1


# --- Auth tests ---


def test_bulk_triage_unauthorized(client, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        json={
            "opportunity_ids": [1, 2],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 401


# --- Validation tests ---


def test_bulk_triage_empty_ids(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 422


def test_bulk_triage_invalid_action(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1],
            "next_action": "invalid_action",
        },
    )
    assert resp.status_code == 422


def test_bulk_triage_single_item(client, operator_a_headers, opportunities_a):
    resp = client.post(
        "/opportunities/bulk-triage",
        headers=operator_a_headers,
        json={
            "opportunity_ids": [1],
            "next_action": "follow",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1
    assert data["skipped"] == 0


# --- Idempotency test ---


def test_bulk_triage_idempotent(client, operator_a_headers, opportunities_a):
    # Apply the same triage twice
    for _ in range(2):
        resp = client.post(
            "/opportunities/bulk-triage",
            headers=operator_a_headers,
            json={
                "opportunity_ids": [1, 2],
                "next_action": "follow",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 2
