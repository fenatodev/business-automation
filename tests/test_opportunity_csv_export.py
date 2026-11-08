"""WP-518 — Opportunity CSV export endpoint tests."""

import csv
import io

from app.models import Opportunity


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opportunity", source="manual"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": source,
            "external_url": f"https://example.com/{title.replace(' ', '-')}",
            "title": title,
            "description": "Test description",
            "budget": "R$ 5000",
            "deadline": "2026-12-31",
            "requirements": "Python, FastAPI",
            "captured_at": "2026-01-01T12:00:00Z",
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Basic CSV export ---


def test_export_csv_returns_csv_content_type(client, admin_headers, operator_a_headers):
    """Export returns CSV with correct content type."""
    company = _create_company(client, admin_headers, name="CsvCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="First Opp")

    res = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment" in res.headers.get("content-disposition", "")


def test_export_csv_contains_data(client, admin_headers, operator_a_headers):
    """Export CSV contains header row and data rows."""
    company = _create_company(client, admin_headers, name="DataCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Alpha")
    _create_opportunity(client, operator_a_headers, company["id"], title="Beta")

    res = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res.status_code == 200

    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["title"] == "Alpha"
    assert rows[1]["title"] == "Beta"


def test_export_csv_columns(client, admin_headers, operator_a_headers):
    """Export CSV has all expected columns."""
    company = _create_company(client, admin_headers, name="ColsCo")
    _create_opportunity(client, operator_a_headers, company["id"])

    res = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res.status_code == 200

    reader = csv.DictReader(io.StringIO(res.text))
    expected_columns = {
        "id", "source", "title", "description", "budget", "deadline",
        "next_action", "outcome", "reason", "final_value",
        "captured_at", "created_at",
    }
    assert set(reader.fieldnames or []) == expected_columns


def test_export_csv_empty_result(client, admin_headers, operator_a_headers):
    """Export with no opportunities returns only header row."""
    company = _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res.status_code == 200

    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 0


# --- Filter by next_action ---


def test_export_csv_filter_next_action(client, admin_headers, operator_a_headers):
    """Filter by next_action returns only matching opportunities."""
    company = _create_company(client, admin_headers, name="FilterCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Pending")
    _create_opportunity(client, operator_a_headers, company["id"], title="Follow")

    # Update one to follow (valid transition from pending)
    opps = client.get("/opportunities", headers=operator_a_headers).json()
    for opp in opps:
        if opp["title"] == "Follow":
            res = client.patch(
                f"/opportunities/{opp['id']}/triage",
                headers=operator_a_headers,
                json={"next_action": "follow"},
            )
            assert res.status_code == 200
            break

    res = client.get(
        "/opportunities/export?next_action=pending",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["title"] == "Pending"


# --- Filter by source ---


def test_export_csv_filter_source(client, admin_headers, operator_a_headers):
    """Filter by source returns only matching opportunities."""
    company = _create_company(client, admin_headers, name="SourceCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Manual", source="manual")
    _create_opportunity(client, operator_a_headers, company["id"], title="Intake", source="intake")

    res = client.get(
        "/opportunities/export?source=intake",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["title"] == "Intake"


# --- Filter by search query ---


def test_export_csv_filter_search(client, admin_headers, operator_a_headers):
    """Filter by search query returns matching opportunities."""
    company = _create_company(client, admin_headers, name="SearchCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Website Project")
    _create_opportunity(client, operator_a_headers, company["id"], title="App Mobile")

    res = client.get(
        "/opportunities/export?q=website",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["title"] == "Website Project"


# --- Tenant isolation ---


def test_export_csv_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot export Operator B's opportunities."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    company_b = _create_company(client, admin_headers, name="TenantB")

    _create_opportunity(client, operator_a_headers, company_a["id"], title="A Opp")
    _create_opportunity(client, operator_b_headers, company_b["id"], title="B Opp")

    res_a = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res_a.status_code == 200
    reader_a = csv.DictReader(io.StringIO(res_a.text))
    rows_a = list(reader_a)
    assert len(rows_a) == 1
    assert rows_a[0]["title"] == "A Opp"

    res_b = client.get(
        "/opportunities/export",
        headers=operator_b_headers,
    )
    assert res_b.status_code == 200
    reader_b = csv.DictReader(io.StringIO(res_b.text))
    rows_b = list(reader_b)
    assert len(rows_b) == 1
    assert rows_b[0]["title"] == "B Opp"


# --- Auth requirements ---


def test_export_csv_requires_auth(client):
    """Export requires authentication."""
    res = client.get("/opportunities/export")
    assert res.status_code in (401, 403)


# --- UTF-8 encoding ---


def test_export_csv_utf8_encoding(client, admin_headers, operator_a_headers):
    """Export handles UTF-8 characters correctly."""
    company = _create_company(client, admin_headers, name="Utf8Co")
    _create_opportunity(
        client,
        operator_a_headers,
        company["id"],
        title="Projeto com acentos: ã é í ó ú ç Ñ",
    )

    res = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 1
    assert "acentos" in rows[0]["title"]
    assert "ã" in rows[0]["title"]


# --- Null fields ---


def test_export_csv_null_fields(client, admin_headers, operator_a_headers):
    """Export handles null fields gracefully."""
    company = _create_company(client, admin_headers, name="NullCo")
    _create_opportunity(
        client,
        operator_a_headers,
        company["id"],
        title="Minimal Opp",
    )

    res = client.get(
        "/opportunities/export",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 1
    # outcome and reason should be empty strings for unclosed opportunities
    assert rows[0]["outcome"] == ""
    assert rows[0]["reason"] == ""
    assert rows[0]["final_value"] == ""
