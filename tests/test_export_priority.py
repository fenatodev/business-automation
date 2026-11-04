"""WP-246 — Export CSV with priority score column.

The opportunities export CSV now includes the calculated priority score
and level, allowing the operator to analyze priorities in a spreadsheet.
"""

from datetime import datetime, timedelta

import pytest

from app.models import Company, Opportunity
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


@pytest.fixture
def opportunities_a(company_a):
    """Create opportunities with different priority factors."""
    with TestingSessionLocal() as db:
        # High priority: urgent deadline, budget, pending status, intake source
        opp1 = Opportunity(
            company_id=1, source="intake", external_url="https://example.com/1",
            title="Urgent Site", description="Test", captured_at=datetime.now(),
            budget="5000", deadline=(datetime.now() + timedelta(days=3)).isoformat(),
            next_action="pending",
        )
        # Medium priority: moderate deadline, no budget, follow status
        opp2 = Opportunity(
            company_id=1, source="manual", external_url="https://example.com/2",
            title="Normal App", description="Test", captured_at=datetime.now(),
            deadline=(datetime.now() + timedelta(days=20)).isoformat(),
            next_action="follow",
        )
        # Low priority: far deadline, no budget, done status
        opp3 = Opportunity(
            company_id=1, source="import", external_url="https://example.com/3",
            title="Old Project", description="Test", captured_at=datetime.now(),
            deadline=(datetime.now() + timedelta(days=60)).isoformat(),
            next_action="done",
        )
        db.add_all([opp1, opp2, opp3])
        db.commit()


def test_export_csv_includes_priority_columns(client, operator_a_headers, opportunities_a):
    """Export CSV includes priority score and level columns."""
    response = client.get(
        "/opportunities/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    header = lines[0]
    assert "Prioridade" in header
    assert "Nível prioridade" in header


def test_export_csv_priority_column_count(client, operator_a_headers, opportunities_a):
    """Export CSV has 13 columns (original 11 + priority + level)."""
    response = client.get(
        "/opportunities/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    header = lines[0].split(",")
    assert len(header) == 13


def test_export_csv_priority_score_is_numeric(client, operator_a_headers, opportunities_a):
    """Priority score column contains numeric values."""
    response = client.get(
        "/opportunities/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    for line in lines[1:]:  # skip header
        parts = line.split(",")
        if len(parts) >= 12:
            score = parts[-2]  # second to last column
            assert score.strip().isdigit()


def test_export_csv_priority_level_is_valid(client, operator_a_headers, opportunities_a):
    """Priority level column contains valid values (high/medium/low)."""
    response = client.get(
        "/opportunities/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    valid_levels = {"high", "medium", "low"}
    for line in lines[1:]:  # skip header
        parts = line.split(",")
        if len(parts) >= 13:
            level = parts[-1].strip()
            assert level in valid_levels, f"Invalid priority level: {level}"


def test_export_csv_high_priority_opportunity(client, operator_a_headers, opportunities_a):
    """High priority opportunity has score >= 70."""
    response = client.get(
        "/opportunities/export.csv",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    for line in lines[1:]:
        parts = line.split(",")
        if "Urgent Site" in line:
            score = int(parts[-2].strip())
            assert score >= 70, f"Expected high priority (>=70), got {score}"
            assert parts[-1].strip() == "high"


def test_export_csv_respects_filters(client, operator_a_headers, opportunities_a):
    """Export CSV with filters still includes priority columns."""
    response = client.get(
        "/opportunities/export.csv?next_action=pending",
        headers=operator_a_headers,
    )
    assert response.status_code == 200
    content = response.text
    lines = content.strip().split("\n")
    header = lines[0]
    assert "Prioridade" in header
    # Only 1 opportunity with pending status
    assert len(lines) == 2  # header + 1 data row


def test_export_csv_requires_auth(client, opportunities_a):
    """Export CSV requires authentication."""
    response = client.get("/opportunities/export.csv")
    assert response.status_code in (401, 403)
