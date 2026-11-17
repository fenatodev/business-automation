"""Lead conversion analytics endpoint tests.

Tests the GET /leads/conversion-analytics endpoint that calculates
lead-to-customer conversion metrics for the operator dashboard.
"""
from datetime import datetime, timedelta, timezone

from conftest import TestingSessionLocal


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Lead", phone="11999999999", source="manual"):
    res = client.post(
        "/leads",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": phone,
            "source": source,
        },
    )
    assert res.status_code == 200
    return res.json()


def _convert_lead(client, headers, lead_id):
    res = client.post(f"/leads/{lead_id}/convert", headers=headers)
    assert res.status_code == 200
    return res.json()


def _backdate_lead_created(lead_id, days_ago):
    """Set lead.created_at to `days_ago` days ago."""
    from sqlalchemy import text

    created_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    with TestingSessionLocal() as db:
        db.execute(
            text("UPDATE leads SET created_at = :ca WHERE id = :id"),
            {"ca": created_at, "id": lead_id},
        )
        db.commit()


def _backdate_customer_created(customer_id, days_ago):
    """Set customer.created_at to `days_ago` days ago."""
    from sqlalchemy import text

    created_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    with TestingSessionLocal() as db:
        db.execute(
            text("UPDATE customers SET created_at = :ca WHERE id = :id"),
            {"ca": created_at, "id": customer_id},
        )
        db.commit()


def test_conversion_analytics_empty_when_no_leads(
    client, admin_headers, operator_a_headers
):
    """Returns zeros when no leads exist."""
    _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 0
    assert data["converted_leads"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["avg_days_to_convert"] is None
    assert data["conversions_by_source"] == {}


def test_conversion_analytics_no_conversions(
    client, admin_headers, operator_a_headers
):
    """Returns 0% conversion rate when leads exist but none converted."""
    company = _create_company(client, admin_headers, name="NoConvCo")
    _create_lead(client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111")
    _create_lead(client, operator_a_headers, company["id"], name="Lead 2", phone="11922222222")

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 2
    assert data["converted_leads"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["avg_days_to_convert"] is None


def test_conversion_analytics_full_conversion(
    client, admin_headers, operator_a_headers
):
    """Returns 100% conversion rate when all leads are converted."""
    company = _create_company(client, admin_headers, name="FullCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111")
    _convert_lead(client, operator_a_headers, lead["id"])

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 1
    assert data["converted_leads"] == 1
    assert data["conversion_rate"] == 100.0


def test_conversion_analytics_partial_conversion(
    client, admin_headers, operator_a_headers
):
    """Returns correct partial conversion rate."""
    company = _create_company(client, admin_headers, name="PartialCo")
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="Lead 2", phone="11922222222")
    lead3 = _create_lead(client, operator_a_headers, company["id"], name="Lead 3", phone="11933333333")
    _convert_lead(client, operator_a_headers, lead1["id"])
    _convert_lead(client, operator_a_headers, lead2["id"])
    # lead3 not converted

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 3
    assert data["converted_leads"] == 2
    assert data["conversion_rate"] == 66.7


def test_conversion_analytics_avg_days_to_convert(
    client, admin_headers, operator_a_headers
):
    """Calculates average days to convert correctly."""
    company = _create_company(client, admin_headers, name="DaysCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111")
    customer = _convert_lead(client, operator_a_headers, lead["id"])

    # Lead created 10 days ago, customer created 5 days ago => 5 days to convert
    _backdate_lead_created(lead["id"], 10)
    _backdate_customer_created(customer["id"], 5)

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["avg_days_to_convert"] is not None
    # Should be approximately 5 days (within 0.5 day tolerance)
    assert 4.5 <= data["avg_days_to_convert"] <= 5.5


def test_conversion_analytics_conversions_by_source(
    client, admin_headers, operator_a_headers
):
    """Breaks down conversions by lead source."""
    company = _create_company(client, admin_headers, name="SourceCo")
    lead1 = _create_lead(
        client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111", source="99freelas"
    )
    lead2 = _create_lead(
        client, operator_a_headers, company["id"], name="Lead 2", phone="11922222222", source="intake"
    )
    lead3 = _create_lead(
        client, operator_a_headers, company["id"], name="Lead 3", phone="11933333333", source="99freelas"
    )
    lead4 = _create_lead(
        client, operator_a_headers, company["id"], name="Lead 4", phone="11944444444", source="manual"
    )
    _convert_lead(client, operator_a_headers, lead1["id"])
    _convert_lead(client, operator_a_headers, lead2["id"])
    _convert_lead(client, operator_a_headers, lead3["id"])
    # lead4 not converted

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["conversions_by_source"]["99freelas"] == 2
    assert data["conversions_by_source"]["intake"] == 1
    assert "manual" not in data["conversions_by_source"]


def test_conversion_analytics_tenant_isolation(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Only returns analytics for the authenticated tenant."""
    company_a = _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")

    lead_a = _create_lead(client, operator_a_headers, company_a["id"], name="Lead A", phone="11911111111")
    lead_b = _create_lead(client, operator_b_headers, company_b["id"], name="Lead B", phone="11922222222")
    _convert_lead(client, operator_a_headers, lead_a["id"])
    _convert_lead(client, operator_b_headers, lead_b["id"])

    res_a = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    data_a = res_a.json()
    assert data_a["total_leads"] == 1
    assert data_a["converted_leads"] == 1

    res_b = client.get(
        "/leads/conversion-analytics",
        headers=operator_b_headers,
    )
    data_b = res_b.json()
    assert data_b["total_leads"] == 1
    assert data_b["converted_leads"] == 1


def test_conversion_analytics_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/leads/conversion-analytics")
    assert res.status_code in (401, 403)


def test_conversion_analytics_multiple_sources_with_zero_conversion(
    client, admin_headers, operator_a_headers
):
    """Conversions by source only includes converted leads."""
    company = _create_company(client, admin_headers, name="ZeroCo")
    _create_lead(
        client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111", source="99freelas"
    )
    _create_lead(
        client, operator_a_headers, company["id"], name="Lead 2", phone="11922222222", source="intake"
    )

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 2
    assert data["converted_leads"] == 0
    assert data["conversions_by_source"] == {}


def test_conversion_analytics_response_fields(
    client, admin_headers, operator_a_headers
):
    """Response includes all expected fields with correct types."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111")
    _convert_lead(client, operator_a_headers, lead["id"])

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_leads" in data
    assert "converted_leads" in data
    assert "conversion_rate" in data
    assert "avg_days_to_convert" in data
    assert "conversions_by_source" in data
    assert isinstance(data["total_leads"], int)
    assert isinstance(data["converted_leads"], int)
    assert isinstance(data["conversion_rate"], (int, float))
    assert isinstance(data["conversions_by_source"], dict)


def test_conversion_analytics_idempotent_convert(
    client, admin_headers, operator_a_headers
):
    """Converting the same lead twice doesn't double count."""
    company = _create_company(client, admin_headers, name="IdemCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Lead 1", phone="11911111111")
    _convert_lead(client, operator_a_headers, lead["id"])
    # Second convert should return existing customer without creating duplicate
    _convert_lead(client, operator_a_headers, lead["id"])

    res = client.get(
        "/leads/conversion-analytics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] == 1
    assert data["converted_leads"] == 1
    assert data["conversion_rate"] == 100.0
