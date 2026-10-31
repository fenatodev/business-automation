"""WP-106 — Exportação CSV de dados do operador."""

from datetime import datetime

import pytest

from app.models import Company, Customer, Lead, Opportunity
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
        for i in range(3):
            db.add(Opportunity(
                company_id=1,
                source="intake",
                external_url=f"https://example.com/opp-{i}",
                title=f"Opportunity {i}",
                description=f"Description {i}",
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
            external_url="https://example.com/opp-b",
            title="Secret Opportunity B",
            description="Should not appear",
            captured_at=datetime.now(),
            next_action="pending",
        ))
        db.commit()


@pytest.fixture
def leads_a(company_a):
    """Create leads in company A."""
    with TestingSessionLocal() as db:
        for i in range(3):
            db.add(Lead(
                company_id=1,
                name=f"Lead {i}",
                phone=f"551199999{i:04d}",
                source="web",
                interest=f"Interest {i}",
                status="new",
            ))
        db.commit()


@pytest.fixture
def leads_b(company_b):
    """Create leads in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        db.add(Lead(
            company_id=2,
            name="Secret Lead B",
            phone="5511988888888",
            source="web",
            interest="Should not appear",
            status="new",
        ))
        db.commit()


@pytest.fixture
def customers_a(company_a):
    """Create customers in company A."""
    with TestingSessionLocal() as db:
        for i in range(3):
            db.add(Customer(
                company_id=1,
                name=f"Customer {i}",
                phone=f"551197777{i:04d}",
                email=f"customer{i}@example.com",
            ))
        db.commit()


@pytest.fixture
def customers_b(company_b):
    """Create customers in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        db.add(Customer(
            company_id=2,
            name="Secret Customer B",
            phone="5511966666666",
            email="secret@example.com",
        ))
        db.commit()


# --- Opportunities export tests ---


def test_export_opportunities_csv(client, operator_a_headers, opportunities_a):
    resp = client.get("/opportunities/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "opportunities.csv" in resp.headers["content-disposition"]
    content = resp.text
    assert "ID" in content
    assert "Titulo" in content
    assert "Opportunity 0" in content
    assert "Opportunity 1" in content
    assert "Opportunity 2" in content


def test_export_opportunities_csv_empty(client, operator_a_headers, company_a):
    resp = client.get("/opportunities/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    # Should have header but no data rows
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # Only header


def test_export_opportunities_csv_tenant_isolation(
        client, operator_a_headers, opportunities_a, opportunities_b):
    resp = client.get("/opportunities/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Opportunity 0" in content
    assert "Secret Opportunity B" not in content


def test_export_opportunities_csv_requires_auth(client):
    resp = client.get("/opportunities/export.csv")
    assert resp.status_code in (401, 403)


def test_export_opportunities_csv_has_all_fields(client, operator_a_headers, opportunities_a):
    resp = client.get("/opportunities/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Descricao" in content
    assert "Status" in content
    assert "Orçamento" in content
    assert "Prazo" in content
    assert "Requisitos" in content
    assert "URL" in content
    assert "Fonte" in content
    assert "Nota triagem" in content
    assert "Capturada em" in content


# --- Leads export tests ---


def test_export_leads_csv(client, operator_a_headers, leads_a):
    resp = client.get("/leads/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "leads.csv" in resp.headers["content-disposition"]
    content = resp.text
    assert "ID" in content
    assert "Nome" in content
    assert "Lead 0" in content
    assert "Lead 1" in content
    assert "Lead 2" in content


def test_export_leads_csv_empty(client, operator_a_headers, company_a):
    resp = client.get("/leads/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # Only header


def test_export_leads_csv_tenant_isolation(
        client, operator_a_headers, leads_a, leads_b):
    resp = client.get("/leads/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Lead 0" in content
    assert "Secret Lead B" not in content


def test_export_leads_csv_requires_auth(client):
    resp = client.get("/leads/export.csv")
    assert resp.status_code in (401, 403)


def test_export_leads_csv_has_all_fields(client, operator_a_headers, leads_a):
    resp = client.get("/leads/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Telefone" in content
    assert "Fonte" in content
    assert "Interesse" in content
    assert "Status" in content
    assert "Criado em" in content


# --- Customers export tests ---


def test_export_customers_csv(client, operator_a_headers, customers_a):
    resp = client.get("/customers/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "customers.csv" in resp.headers["content-disposition"]
    content = resp.text
    assert "ID" in content
    assert "Nome" in content
    assert "Customer 0" in content
    assert "Customer 1" in content
    assert "Customer 2" in content


def test_export_customers_csv_empty(client, operator_a_headers, company_a):
    resp = client.get("/customers/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # Only header


def test_export_customers_csv_tenant_isolation(
        client, operator_a_headers, customers_a, customers_b):
    resp = client.get("/customers/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Customer 0" in content
    assert "Secret Customer B" not in content


def test_export_customers_csv_requires_auth(client):
    resp = client.get("/customers/export.csv")
    assert resp.status_code in (401, 403)


def test_export_customers_csv_has_all_fields(client, operator_a_headers, customers_a):
    resp = client.get("/customers/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Telefone" in content
    assert "E-mail" in content
    assert "Lead origem" in content
    assert "Criado em" in content
