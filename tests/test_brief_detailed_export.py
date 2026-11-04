"""WP-250 — Detailed proposal brief CSV export.

The brief export CSV now includes all detailed fields: diagnosis, scope,
deliverables, acceptance criteria, assumptions, and risks — in addition
to the basic fields (ID, opportunity, title, reference, status, created).
"""

from datetime import datetime

import pytest

from app.models import Company, Opportunity, ProposalBrief
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


@pytest.fixture
def brief_a(company_a):
    """Create a brief with all fields populated."""
    brief_id = None
    with TestingSessionLocal() as db:
        opp = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/1",
            title="Test Opportunity", description="Test", captured_at=datetime.now(),
            next_action="proposal",
        )
        db.add(opp)
        db.flush()

        brief = ProposalBrief(
            opportunity_id=opp.id,
            offer_reference="REF-001",
            diagnosis="Diagnóstico de teste",
            scope="Escopo de teste",
            deliverables="Entregáveis de teste",
            acceptance_criteria="Critérios de teste",
            assumptions="Hipóteses de teste",
            risks="Riscos de teste",
            status="draft",
        )
        db.add(brief)
        db.commit()
        brief_id = brief.id
    return brief_id


def test_export_csv_includes_detailed_columns(client, operator_a_headers, brief_a):
    """Export CSV includes all detailed columns."""
    response = client.get(
        "/proposal-briefs/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    header = content.strip().split("\n")[0]
    assert "Diagnóstico" in header
    assert "Escopo" in header
    assert "Entregáveis" in header
    assert "Critérios" in header
    assert "Hipóteses" in header
    assert "Riscos" in header


def test_export_csv_column_count(client, operator_a_headers, brief_a):
    """Export CSV has 12 columns (6 basic + 6 detailed)."""
    response = client.get(
        "/proposal-briefs/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    header = content.strip().split("\n")[0].split(",")
    assert len(header) == 12


def test_export_csv_includes_detailed_data(client, operator_a_headers, brief_a):
    """Export CSV includes the actual detailed field values."""
    response = client.get(
        "/proposal-briefs/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    # Skip header, check data row
    data_line = lines[1]
    assert "Diagnóstico de teste" in data_line
    assert "Escopo de teste" in data_line
    assert "Entregáveis de teste" in data_line
    assert "Critérios de teste" in data_line
    assert "Hipóteses de teste" in data_line
    assert "Riscos de teste" in data_line


def test_export_csv_handles_null_detailed_fields(client, operator_a_headers, company_a):
    """Export CSV handles null detailed fields gracefully."""
    with TestingSessionLocal() as db:
        opp = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/null",
            title="Null Fields", description="Test", captured_at=datetime.now(),
            next_action="proposal",
        )
        db.add(opp)
        db.flush()

        brief = ProposalBrief(
            opportunity_id=opp.id,
            offer_reference="REF-NULL",
            diagnosis="",
            scope="",
            deliverables="",
            acceptance_criteria="",
            assumptions=None,
            risks=None,
            status="draft",
        )
        db.add(brief)
        db.commit()

    response = client.get(
        "/proposal-briefs/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    # Should have header + at least 1 data row
    assert len(lines) >= 2


def test_export_csv_respects_status_filter(client, operator_a_headers, brief_a):
    """Export CSV with status filter still includes detailed columns."""
    response = client.get(
        "/proposal-briefs/export.csv?status=draft",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    header = content.strip().split("\n")[0]
    assert "Diagnóstico" in header


def test_export_csv_respects_search_filter(client, operator_a_headers, brief_a):
    """Export CSV with search filter still includes detailed columns."""
    response = client.get(
        "/proposal-briefs/export.csv?q=REF-001",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    header = content.strip().split("\n")[0]
    assert "Diagnóstico" in header
    # Should find the brief with matching reference
    assert "REF-001" in content


def test_export_csv_requires_auth(client, brief_a):
    """Export CSV requires authentication."""
    response = client.get("/proposal-briefs/export.csv")
    assert response.status_code in (401, 403)
