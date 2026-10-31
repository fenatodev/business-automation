"""WP-169/170 — Bulk delete for customers and leads.

Tests that bulk delete endpoints are tenant-isolated, return correct counts,
and properly skip IDs that don't belong to the tenant.
"""
import pytest

from app.models import Company, Customer, Lead
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
def customers_a(company_a):
    """Create customers in company A."""
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=1, name="Customer A1", phone="11900000001"))
        db.add(Customer(company_id=1, name="Customer A2", phone="11900000002"))
        db.commit()


@pytest.fixture
def customers_b(company_b):
    """Create customers in company B."""
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=2, name="Customer B1", phone="11900000003"))
        db.commit()


@pytest.fixture
def leads_a(company_a):
    """Create leads in company A."""
    with TestingSessionLocal() as db:
        db.add(Lead(company_id=1, name="Lead A1", phone="11910000001", source="manual"))
        db.add(Lead(company_id=1, name="Lead A2", phone="11910000002", source="manual"))
        db.commit()


@pytest.fixture
def leads_b(company_b):
    """Create leads in company B."""
    with TestingSessionLocal() as db:
        db.add(Lead(company_id=2, name="Lead B1", phone="11910000003", source="manual"))
        db.commit()


class TestCustomerBulkDelete:
    """Test POST /customers/bulk-delete."""

    def test_bulk_delete_customers(self, client, operator_a_headers, customers_a):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [1, 2],
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2
        assert resp.json()["skipped"] == []

    def test_bulk_delete_returns_deleted_ids(self, client, operator_a_headers, customers_a):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [1, 2],
        }, headers=operator_a_headers)
        assert sorted(resp.json()["deleted_ids"]) == [1, 2]

    def test_bulk_delete_skips_nonexistent(self, client, operator_a_headers, customers_a):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [1, 99999],
        }, headers=operator_a_headers)
        assert resp.json()["deleted"] == 1
        assert 99999 in resp.json()["skipped"]

    def test_bulk_delete_tenant_isolation(self, client, operator_a_headers, customers_b):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [1],
        }, headers=operator_a_headers)
        assert resp.json()["deleted"] == 0
        assert 1 in resp.json()["skipped"]

    def test_bulk_delete_requires_auth(self, client):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [1],
        })
        assert resp.status_code in (401, 403)

    def test_bulk_delete_single_item(self, client, operator_a_headers, customers_a):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [1],
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 1

    def test_bulk_delete_empty_rejected(self, client, operator_a_headers):
        resp = client.post("/customers/bulk-delete", json={
            "customer_ids": [],
        }, headers=operator_a_headers)
        assert resp.status_code == 422

    def test_bulk_delete_actually_removes(self, client, operator_a_headers, customers_a):
        client.post("/customers/bulk-delete", json={
            "customer_ids": [1],
        }, headers=operator_a_headers)
        resp = client.get("/customers/1", headers=operator_a_headers)
        assert resp.status_code == 404


class TestLeadBulkDelete:
    """Test POST /leads/bulk-delete."""

    def test_bulk_delete_leads(self, client, operator_a_headers, leads_a):
        resp = client.post("/leads/bulk-delete", json={
            "lead_ids": [1, 2],
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2
        assert resp.json()["skipped"] == []

    def test_bulk_delete_leads_returns_ids(self, client, operator_a_headers, leads_a):
        resp = client.post("/leads/bulk-delete", json={
            "lead_ids": [1, 2],
        }, headers=operator_a_headers)
        assert sorted(resp.json()["deleted_ids"]) == [1, 2]

    def test_bulk_delete_leads_skips_nonexistent(self, client, operator_a_headers, leads_a):
        resp = client.post("/leads/bulk-delete", json={
            "lead_ids": [1, 99999],
        }, headers=operator_a_headers)
        assert resp.json()["deleted"] == 1
        assert 99999 in resp.json()["skipped"]

    def test_bulk_delete_leads_tenant_isolation(self, client, operator_a_headers, leads_b):
        resp = client.post("/leads/bulk-delete", json={
            "lead_ids": [1],
        }, headers=operator_a_headers)
        assert resp.json()["deleted"] == 0
        assert 1 in resp.json()["skipped"]

    def test_bulk_delete_leads_requires_auth(self, client):
        resp = client.post("/leads/bulk-delete", json={
            "lead_ids": [1],
        })
        assert resp.status_code in (401, 403)

    def test_bulk_delete_leads_empty_rejected(self, client, operator_a_headers):
        resp = client.post("/leads/bulk-delete", json={
            "lead_ids": [],
        }, headers=operator_a_headers)
        assert resp.status_code == 422

    def test_bulk_delete_leads_actually_removes(self, client, operator_a_headers, leads_a):
        client.post("/leads/bulk-delete", json={
            "lead_ids": [1],
        }, headers=operator_a_headers)
        resp = client.get("/leads/1", headers=operator_a_headers)
        assert resp.status_code == 404
