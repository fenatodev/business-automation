"""WP-115 — Bulk lead status update."""

import pytest

from app.models import Company, Lead
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
def leads_a(company_a):
    with TestingSessionLocal() as db:
        db.add(Lead(id=1, company_id=1, name="Lead 1", phone="111", source="web", status="new"))
        db.add(Lead(id=2, company_id=1, name="Lead 2", phone="222", source="web", status="new"))
        db.add(Lead(id=3, company_id=1, name="Lead 3", phone="333", source="web", status="contacted"))
        db.commit()


@pytest.fixture
def lead_b(company_b):
    with TestingSessionLocal() as db:
        db.add(Lead(id=4, company_id=2, name="Lead B", phone="444", source="web", status="new"))
        db.commit()


def test_bulk_update_status(client, operator_a_headers, leads_a):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [1, 2], "status": "qualified"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2
    assert data["updated_ids"] == [1, 2]
    assert data["skipped"] == []


def test_bulk_update_mixed_ids(client, operator_a_headers, leads_a):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [1, 9999], "status": "proposal"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1
    assert data["updated_ids"] == [1]
    assert data["skipped"] == [9999]


def test_bulk_update_tenant_isolation(client, operator_a_headers, leads_a, lead_b):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [4], "status": "won"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 0
    assert data["skipped"] == [4]


def test_bulk_update_all_selected(client, operator_a_headers, leads_a):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [1, 2, 3], "status": "lost"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 3


def test_bulk_update_requires_auth(client, leads_a):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [1], "status": "new"},
    )
    assert resp.status_code in (401, 403)


def test_bulk_update_empty_ids_rejected(client, operator_a_headers, leads_a):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [], "status": "new"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 422


def test_bulk_update_invalid_status_rejected(client, operator_a_headers, leads_a):
    resp = client.post(
        "/leads/bulk-status",
        json={"lead_ids": [1], "status": "invalid_status"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 422


def test_bulk_update_reflected_in_list(client, operator_a_headers, leads_a):
    client.post(
        "/leads/bulk-status",
        json={"lead_ids": [1], "status": "qualified"},
        headers=operator_a_headers,
    )
    resp = client.get("/leads", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    lead1 = [l for l in data if l["id"] == 1]
    assert len(lead1) == 1
    assert lead1[0]["status"] == "qualified"
