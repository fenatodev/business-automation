"""WP-223 — Recent activities in dashboard.

The dashboard shows aggregate counts but not what actually happened recently.
This endpoint returns the most recent activities across all entities, giving
the operator quick context on what's happening.
"""

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def test_recent_activities_returns_list(client, admin_headers, operator_a_headers):
    """GET /internal-tasks/recent-activities returns a list."""
    _create_company(client, admin_headers, "RecentActivitiesCo")

    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
    assert isinstance(data["activities"], list)


def test_recent_activities_default_limit(client, admin_headers, operator_a_headers):
    """Default limit is 20 activities."""
    _create_company(client, admin_headers, "LimitTestCo")
    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    data = response.json()
    assert len(data["activities"]) <= 20


def test_recent_activities_custom_limit(client, admin_headers, operator_a_headers):
    """Custom limit parameter works."""
    _create_company(client, admin_headers, "CustomLimitCo")
    response = client.get("/internal-tasks/recent-activities?limit=5", headers=operator_a_headers)
    data = response.json()
    assert len(data["activities"]) <= 5


def test_recent_activities_includes_opportunities(client, admin_headers, operator_a_headers):
    """Opportunities appear in recent activities."""
    company = _create_company(client, admin_headers, "OppActivitiesCo")
    opp = client.post(
        "/opportunities",
        json={
            "title": "Recent Opp",
            "description": "Test opportunity",
            "external_url": "https://example.com/recent-opp",
            "source": "manual",
            "captured_at": "2026-01-01T00:00:00",
        },
        headers=operator_a_headers,
    )
    assert opp.status_code in (200, 201), opp.text
    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    opp_activities = [a for a in data["activities"] if a["type"] == "opportunity"]
    assert len(opp_activities) >= 1, f"Expected at least 1 opportunity activity, got {data['activities']}"


def test_recent_activities_includes_conversations(client, admin_headers, operator_a_headers):
    """Conversations appear in recent activities."""
    company = _create_company(client, admin_headers, "ConvActivitiesCo")
    # Create a lead first, then a conversation linked to it
    lead = client.post(
        "/leads",
        json={"name": "Conv Lead", "phone": "+5511999999998", "source": "manual", "company_id": company["id"]},
        headers=operator_a_headers,
    )
    assert lead.status_code in (200, 201), lead.text
    lead_id = lead.json()["id"]
    conv = client.post(
        "/conversations",
        json={"company_id": company["id"], "channel": "web", "lead_id": lead_id},
        headers=operator_a_headers,
    )
    assert conv.status_code in (200, 201), conv.text
    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    data = response.json()
    conv_activities = [a for a in data["activities"] if a["type"] == "conversation"]
    assert len(conv_activities) >= 1


def test_recent_activities_includes_leads(client, admin_headers, operator_a_headers):
    """Leads appear in recent activities."""
    company = _create_company(client, admin_headers, "LeadActivitiesCo")
    lead = client.post(
        "/leads",
        json={"name": "Recent Lead", "phone": "+5511999999999", "source": "manual", "company_id": company["id"]},
        headers=operator_a_headers,
    )
    assert lead.status_code in (200, 201), lead.text
    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    data = response.json()
    lead_activities = [a for a in data["activities"] if a["type"] == "lead"]
    assert len(lead_activities) >= 1, f"Expected at least 1 lead activity, got {data['activities']}"


def test_recent_activities_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Activities are isolated by tenant."""
    _create_company(client, admin_headers, "TenantA")
    _create_company(client, admin_headers, "TenantB")

    # Create opportunity in company A (operator_a)
    client.post(
        "/opportunities",
        json={
            "title": "Opp in A",
            "description": "Should not appear in B",
            "external_url": "https://example.com/a",
            "source": "manual",
            "captured_at": "2026-01-01T00:00:00",
        },
        headers=operator_a_headers,
    )

    # Fetch activities for company B (operator_b)
    response = client.get("/internal-tasks/recent-activities", headers=operator_b_headers)
    data = response.json()

    for activity in data["activities"]:
        if activity["type"] == "opportunity":
            assert activity["title"] != "Opp in A"


def test_recent_activities_requires_auth(client):
    """Recent activities endpoint requires authentication."""
    response = client.get("/internal-tasks/recent-activities")
    assert response.status_code in (401, 403)


def test_recent_activities_ordered_by_time(client, admin_headers, operator_a_headers):
    """Activities are ordered by created_at descending."""
    _create_company(client, admin_headers, "OrderTestCo")
    for i in range(3):
        client.post(
            "/leads",
            json={"name": f"Lead {i}", "phone": f"+551199999999{i}", "source": "manual"},
            headers=operator_a_headers,
        )

    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    data = response.json()
    timestamps = [a["created_at"] for a in data["activities"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_recent_activities_activity_has_required_fields(client, admin_headers, operator_a_headers):
    """Each activity has type, title, created_at, and id."""
    _create_company(client, admin_headers, "FieldsTestCo")
    client.post(
        "/leads",
        json={"name": "Field Test Lead", "phone": "+5511999999990", "source": "manual"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    data = response.json()

    for activity in data["activities"]:
        assert "type" in activity
        assert "title" in activity
        assert "created_at" in activity
        assert "id" in activity


def test_recent_activities_empty_when_no_data(client, admin_headers, operator_a_headers):
    """Returns empty list when company has no activities."""
    _create_company(client, admin_headers, "EmptyCo")
    response = client.get("/internal-tasks/recent-activities", headers=operator_a_headers)
    data = response.json()
    assert data["activities"] == []


def test_recent_activities_filter_by_type(client, admin_headers, operator_a_headers):
    """Can filter activities by type."""
    _create_company(client, admin_headers, "FilterTypeCo")
    client.post(
        "/leads",
        json={"name": "Filter Test Lead", "phone": "+5511999999991", "source": "manual"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/recent-activities?type=lead", headers=operator_a_headers)
    data = response.json()

    for activity in data["activities"]:
        assert activity["type"] == "lead"
