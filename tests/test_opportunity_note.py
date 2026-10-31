"""WP-113 — Notas em oportunidades via PATCH /opportunities/{id}."""

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
def opportunity_a(company_a):
    with TestingSessionLocal() as db:
        from datetime import datetime, timezone
        db.add(Opportunity(
            id=1, company_id=1, source="intake", external_url="https://example.com/1",
            title="Opportunity A", description="Description A",
            captured_at=datetime.now(timezone.utc),
        ))
        db.commit()


@pytest.fixture
def opportunity_b(company_b):
    with TestingSessionLocal() as db:
        from datetime import datetime, timezone
        db.add(Opportunity(
            id=2, company_id=2, source="intake", external_url="https://example.com/2",
            title="Opportunity B", description="Description B",
            captured_at=datetime.now(timezone.utc),
        ))
        db.commit()


def test_update_triage_note(client, operator_a_headers, opportunity_a):
    resp = client.patch(
        "/opportunities/1",
        json={"triage_note": "Cliente prefere orçamento em R$"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["triage_note"] == "Cliente prefere orçamento em R$"
    assert data["title"] == "Opportunity A"


def test_update_triage_note_clears_existing(client, operator_a_headers, opportunity_a):
    # First set a note
    client.patch(
        "/opportunities/1",
        json={"triage_note": "Nota anterior"},
        headers=operator_a_headers,
    )
    # Then clear it
    resp = client.patch(
        "/opportunities/1",
        json={"triage_note": None},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["triage_note"] is None


def test_update_triage_note_preserves_title(client, operator_a_headers, opportunity_a):
    resp = client.patch(
        "/opportunities/1",
        json={"triage_note": "Apenas nota"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["triage_note"] == "Apenas nota"
    assert data["title"] == "Opportunity A"
    assert data["description"] == "Description A"


def test_update_triage_note_and_title_together(client, operator_a_headers, opportunity_a):
    resp = client.patch(
        "/opportunities/1",
        json={"title": "Novo título", "triage_note": "Nota com título"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Novo título"
    assert data["triage_note"] == "Nota com título"


def test_update_triage_note_tenant_isolation(client, operator_a_headers, opportunity_a, opportunity_b):
    resp = client.patch(
        "/opportunities/2",
        json={"triage_note": "Hack"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_update_triage_note_not_found(client, operator_a_headers, company_a):
    resp = client.patch(
        "/opportunities/9999",
        json={"triage_note": "Ghost"},
        headers=operator_a_headers,
    )
    assert resp.status_code == 404


def test_update_triage_note_requires_auth(client, opportunity_a):
    resp = client.patch(
        "/opportunities/1",
        json={"triage_note": "Sem auth"},
    )
    assert resp.status_code in (401, 403)


def test_update_triage_note_empty_body_rejected(client, operator_a_headers, opportunity_a):
    resp = client.patch(
        "/opportunities/1",
        json={},
        headers=operator_a_headers,
    )
    assert resp.status_code == 400
