"""WP-109 — Exportação CSV de conversas."""

from datetime import datetime

import pytest

from app.models import Company, Conversation, Message
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
def conversations_a(company_a):
    """Create conversations in company A."""
    with TestingSessionLocal() as db:
        for i in range(3):
            db.add(Conversation(
                company_id=1,
                channel="whatsapp" if i % 2 == 0 else "web",
                status="open" if i % 2 == 0 else "closed",
            ))
            db.commit()
            conv_id = db.scalar(
                __import__("sqlalchemy").select(Conversation.id)
                .where(Conversation.company_id == 1)
                .order_by(Conversation.id.desc())
            )
            db.add(Message(
                conversation_id=conv_id,
                sender_type="customer",
                content=f"Hello from conversation {i}",
            ))
            db.commit()


@pytest.fixture
def conversations_b(company_b):
    """Create conversations in company B for tenant isolation."""
    with TestingSessionLocal() as db:
        db.add(Conversation(
            company_id=2,
            channel="telegram",
            status="open",
        ))
        db.commit()
        conv_id = db.scalar(
            __import__("sqlalchemy").select(Conversation.id)
            .where(Conversation.company_id == 2)
            .order_by(Conversation.id.desc())
        )
        db.add(Message(
            conversation_id=conv_id,
            sender_type="customer",
            content="Secret message from company B",
        ))
        db.commit()


def test_export_conversations_csv(client, operator_a_headers, conversations_a):
    resp = client.get("/companies/1/conversations/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "conversations.csv" in resp.headers["content-disposition"]
    content = resp.text
    assert "ID" in content
    assert "Canal" in content
    assert "Status" in content
    assert "Mensagens" in content
    assert "Hello from conversation 0" in content


def test_export_conversations_csv_empty(client, operator_a_headers, company_a):
    resp = client.get("/companies/1/conversations/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # Only header


def test_export_conversations_csv_tenant_isolation(
        client, operator_a_headers, conversations_a, conversations_b):
    resp = client.get("/companies/1/conversations/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Hello from conversation 0" in content
    assert "Secret message from company B" not in content


def test_export_conversations_csv_requires_auth(client):
    resp = client.get("/companies/1/conversations/export.csv")
    assert resp.status_code in (401, 403)


def test_export_conversations_csv_has_all_fields(client, operator_a_headers, conversations_a):
    resp = client.get("/companies/1/conversations/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "Canal" in content
    assert "Status" in content
    assert "Lead" in content
    assert "Customer" in content
    assert "Mensagens" in content
    assert "Criado em" in content


def test_export_conversations_csv_includes_messages(client, operator_a_headers, conversations_a):
    resp = client.get("/companies/1/conversations/export.csv", headers=operator_a_headers)
    assert resp.status_code == 200
    content = resp.text
    assert "[customer]" in content


def test_export_conversations_csv_company_not_found(client, operator_a_headers):
    """The endpoint uses require_operator_company, which returns 403 for mismatched company."""
    resp = client.get("/companies/9999/conversations/export.csv", headers=operator_a_headers)
    assert resp.status_code in (403, 404)
