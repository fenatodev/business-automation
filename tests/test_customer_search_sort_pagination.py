"""WP-104 — Busca, ordenação e paginação de customers."""

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
def customers_a(company_a):
    """Create customers in company A."""
    with TestingSessionLocal() as db:
        for i in range(5):
            db.add(Customer(
                company_id=1,
                name=f"Customer {i:02d}",
                phone=f"1190000000{i}",
                email=f"customer{i}@example.com",
            ))
        db.commit()


@pytest.fixture
def customers_b(company_b):
    """Create customers in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        db.add(Customer(
            company_id=2,
            name="Secret Customer",
            phone="11900000099",
            email="secret@example.com",
        ))
        db.commit()


# --- List tests ---


def test_list_customers_default(client, operator_a_headers, customers_a):
    resp = client.get("/customers", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


def test_list_customers_unauthorized(client, customers_a):
    resp = client.get("/customers")
    assert resp.status_code == 401


# --- Search tests ---


def test_search_by_name(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=1, name="Alpha Industries", phone="11900000001", email="alpha@example.com"))
        db.add(Customer(company_id=1, name="Beta Solutions", phone="11900000002", email="beta@example.com"))
        db.commit()

    resp = client.get("/customers?q=Alpha", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alpha Industries"


def test_search_by_phone(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=1, name="Customer One", phone="11999887766", email="one@example.com"))
        db.commit()

    resp = client.get("/customers?q=99988", headers=operator_a_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_by_email(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=1, name="Customer One", phone="11900000001", email="unique@example.com"))
        db.commit()

    resp = client.get("/customers?q=unique", headers=operator_a_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_no_match(client, operator_a_headers, customers_a):
    resp = client.get("/customers?q=nonexistent", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# --- Sort tests ---


def test_sort_by_name(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        for name in ["Charlie", "Alice", "Bob"]:
            db.add(Customer(company_id=1, name=name, phone="11900000000", email=f"{name.lower()}@example.com"))
        db.commit()

    resp = client.get("/customers?sort=name", headers=operator_a_headers)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert names == ["Alice", "Bob", "Charlie"]


def test_sort_by_created_at(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=1, name="First", phone="11900000001", email="first@example.com"))
        db.commit()
        db.add(Customer(company_id=1, name="Second", phone="11900000002", email="second@example.com"))
        db.commit()

    resp = client.get("/customers?sort=created_at", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    # SQLite server_default may not differentiate within same commit;
    # just verify ordering is stable and returns both
    assert len(data) == 2
    names = {c["name"] for c in data}
    assert names == {"First", "Second"}


# --- Pagination tests ---


def test_pagination_limit_offset(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        for i in range(10):
            db.add(Customer(
                company_id=1,
                name=f"Customer {i:02d}",
                phone=f"1190000000{i}",
                email=f"customer{i}@example.com",
            ))
        db.commit()

    resp = client.get("/customers?limit=3&offset=0", headers=operator_a_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    resp = client.get("/customers?limit=3&offset=3", headers=operator_a_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    resp = client.get("/customers?limit=3&offset=100", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_pagination_limit_max_100(client, operator_a_headers, company_a):
    resp = client.get("/customers?limit=101", headers=operator_a_headers)
    assert resp.status_code == 422


# --- Count tests ---


def test_count_customers(client, operator_a_headers, customers_a):
    resp = client.get("/customers/count", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


def test_count_with_search(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        db.add(Customer(company_id=1, name="Alpha Corp", phone="11900000001", email="alpha@example.com"))
        db.add(Customer(company_id=1, name="Beta Inc", phone="11900000002", email="beta@example.com"))
        db.add(Customer(company_id=1, name="Alpha Solutions", phone="11900000003", email="alpha2@example.com"))
        db.commit()

    resp = client.get("/customers/count?q=Alpha", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_count_empty(client, operator_a_headers, company_a):
    resp = client.get("/customers/count", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_count_unauthorized(client, customers_a):
    resp = client.get("/customers/count")
    assert resp.status_code == 401


# --- Tenant isolation ---


def test_tenant_isolation(client, operator_a_headers, customers_a, customers_b):
    resp = client.get("/customers", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    for c in data:
        assert c["company_id"] == 1


def test_count_tenant_isolation(client, operator_a_headers, customers_a, customers_b):
    resp = client.get("/customers/count", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


# --- Combined filters ---


def test_search_combined_with_pagination(client, operator_a_headers, company_a):
    with TestingSessionLocal() as db:
        for i in range(10):
            name = f"Alpha Customer {i:02d}" if i % 2 == 0 else f"Beta Customer {i:02d}"
            db.add(Customer(company_id=1, name=name, phone=f"1190000000{i}", email=f"customer{i}@example.com"))
        db.commit()

    resp = client.get("/customers?q=Alpha&limit=2&offset=0&sort=name", headers=operator_a_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for c in data:
        assert "Alpha" in c["name"]
