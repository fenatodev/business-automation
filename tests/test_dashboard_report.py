"""WP-523 — Dashboard report CSV export tests."""

import csv
import io


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, title="Test Opportunity"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": "manual",
            "external_url": f"https://example.com/{title.replace(' ', '-')}",
            "title": title,
            "description": "Test description",
            "budget": "R$ 5000",
            "deadline": "2026-12-31",
            "requirements": "Python",
            "captured_at": "2026-01-01T12:00:00Z",
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_customer(client, headers, company_id, name="Test Customer"):
    res = client.post(
        "/customers",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": "11999999999",
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Basic report ---


def test_report_returns_csv(client, admin_headers, operator_a_headers):
    """Report returns CSV with correct content type."""
    company = _create_company(client, admin_headers, name="ReportCo")

    res = client.get(
        f"/companies/{company['id']}/report",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment" in res.headers.get("content-disposition", "")


def test_report_contains_metrics(client, admin_headers, operator_a_headers):
    """Report CSV contains all expected metrics."""
    company = _create_company(client, admin_headers, name="MetricsCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Test")

    res = client.get(
        f"/companies/{company['id']}/report",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    metrics = {row["metric"] for row in rows}
    expected = {
        "period", "total_opportunities", "recent_opportunities",
        "closed_opportunities", "won_opportunities",
        "total_conversations", "open_conversations",
        "total_leads", "converted_leads",
        "total_customers", "total_briefs", "approved_briefs",
    }
    assert expected.issubset(metrics)


def test_report_counts_opportunities(client, admin_headers, operator_a_headers):
    """Report correctly counts opportunities."""
    company = _create_company(client, admin_headers, name="CountCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="First")
    _create_opportunity(client, operator_a_headers, company["id"], title="Second")

    res = client.get(
        f"/companies/{company['id']}/report",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    data = {row["metric"]: row["value"] for row in reader}
    assert int(data["total_opportunities"]) == 2
    assert int(data["recent_opportunities"]) == 2


def test_report_empty_company(client, admin_headers, operator_a_headers):
    """Report for empty company returns zero counts."""
    company = _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        f"/companies/{company['id']}/report",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    data = {row["metric"]: row["value"] for row in reader}
    assert int(data["total_opportunities"]) == 0
    assert int(data["total_conversations"]) == 0
    assert int(data["total_leads"]) == 0
    assert int(data["total_customers"]) == 0


# --- Period filtering ---


def test_report_period_7d(client, admin_headers, operator_a_headers):
    """Report respects 7d period."""
    company = _create_company(client, admin_headers, name="Period7Co")

    res = client.get(
        f"/companies/{company['id']}/report?period=7d",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    data = {row["metric"]: row["value"] for row in reader}
    assert data["period"] == "7d"


def test_report_period_30d(client, admin_headers, operator_a_headers):
    """Report respects 30d period."""
    company = _create_company(client, admin_headers, name="Period30Co")

    res = client.get(
        f"/companies/{company['id']}/report?period=30d",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    data = {row["metric"]: row["value"] for row in reader}
    assert data["period"] == "30d"


def test_report_invalid_period(client, admin_headers, operator_a_headers):
    """Report rejects invalid period."""
    company = _create_company(client, admin_headers, name="InvalidCo")

    res = client.get(
        f"/companies/{company['id']}/report?period=invalid",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


# --- Tenant isolation ---


def test_report_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot export Operator B's report."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    company_b = _create_company(client, admin_headers, name="TenantB")

    res = client.get(
        f"/companies/{company_b['id']}/report",
        headers=operator_a_headers,
    )
    assert res.status_code == 403


# --- Auth requirements ---


def test_report_requires_auth(client):
    """Report requires authentication."""
    res = client.get("/companies/1/report")
    assert res.status_code in (401, 403)


def test_report_company_not_found(client, admin_headers, operator_a_headers):
    """Report returns 404 for non-existent company."""
    res = client.get(
        "/companies/99999/report",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
