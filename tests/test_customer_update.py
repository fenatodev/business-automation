"""WP-110 — Editar customer via PATCH /customers/{id}."""

import pytest

from app.models import Company, Customer
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
def customer_a(company_a):
    with TestingSessionLocal() as db:
        db.add(Customer(id=1, company_id=1, name="Original Name", phone="111", email="old@example.com"))
        db.commit()


@pytest.fixture
def customer_b(company_b):
    with TestingSessionLocal() as db:
        db.add(Customer(id=2, company_id=2, name="Company B Customer", phone="222", email="b@example.com"))
        db.commit()


def test_update_customer_name(client, operator_a_headers, customer_a):
    resp = client.patch("/customers/1", json={"name": "Updated Name"}, headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["phone"] == "111"
    assert data["email"] == "old@example.com"


def test_update_customer_phone(client, operator_a_headers, customer_a):
    resp = client.patch("/customers/1", json={"phone": "999"}, headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json()["phone"] == "999"


def test_update_customer_email(client, operator_a_headers, customer_a):
    resp = client.patch("/customers/1", json={"email": "new@example.com"}, headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@example.com"


def test_update_customer_all_fields(client, operator_a_headers, customer_a):
    resp = client.patch(
        "/customers/1",
        json={"name": "All Fields", "phone": "888", "email": "all@example.com"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "All Fields"
    assert data["phone"] == "888"
    assert data["email"] == "all@example.com"


def test_update_customer_empty_body_rejected(client, operator_a_headers, customer_a):
    resp = client.patch("/customers/1", json={}, headers=operator_a_headers)
    assert resp.status_code == 400


def test_update_customer_tenant_isolation(client, operator_a_headers, customer_a, customer_b):
    resp = client.patch("/customers/2", json={"name": "Hacked"}, headers=operator_a_headers)
    assert resp.status_code == 404


def test_update_customer_not_found(client, operator_a_headers, company_a):
    resp = client.patch("/customers/9999", json={"name": "Ghost"}, headers=operator_a_headers)
    assert resp.status_code == 404


def test_update_customer_requires_auth(client, customer_a):
    resp = client.patch("/customers/1", json={"name": "No Auth"})
    assert resp.status_code in (401, 403)


def test_update_customer_name_max_length(client, operator_a_headers, customer_a):
    resp = client.patch("/customers/1", json={"name": "A" * 121}, headers=operator_a_headers)
    assert resp.status_code == 422


def test_update_customer_preserves_unset_fields(client, operator_a_headers, customer_a):
    resp = client.patch("/customers/1", json={"name": "Only Name"}, headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Only Name"
    assert data["phone"] == "111"
    assert data["email"] == "old@example.com"
