"""WP-228 — Recent activities in dashboard UI.

The dashboard endpoint now includes recent_activities inline, and the UI
renders them in a dedicated section below next actions.
"""

import pytest


class TestRecentActivitiesDashboard:
    """Test recent activities in dashboard."""

    def _create_company(self, client, admin_headers, name="TestCo"):
        resp = client.post("/companies", json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
        }, headers=admin_headers)
        assert resp.status_code == 200, f"Failed to create company: {resp.text}"
        return resp.json()

    def test_dashboard_includes_recent_activities(self, client, admin_headers, operator_a_headers):
        """Dashboard response contains recent_activities key."""
        company = self._create_company(client, admin_headers, "DashActCo")
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Test Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert response.status_code == 200
        data = response.json()
        assert "recent_activities" in data
        assert isinstance(data["recent_activities"], list)

    def test_recent_activities_empty_when_no_data(self, client, admin_headers, operator_a_headers):
        """Recent activities is empty list when no entities exist."""
        self._create_company(client, admin_headers, "EmptyActCo")

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["recent_activities"] == []

    def test_recent_activities_includes_leads(self, client, admin_headers, operator_a_headers):
        """Recent activities shows leads."""
        company = self._create_company(client, admin_headers, "LeadActCo")
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Recent Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        lead_activities = [a for a in data["recent_activities"] if a["type"] == "lead"]
        assert len(lead_activities) >= 1
        assert any("Recent Lead" in a["title"] for a in lead_activities)

    def test_recent_activities_includes_opportunities(self, client, admin_headers, operator_a_headers):
        """Recent activities shows opportunities."""
        company = self._create_company(client, admin_headers, "OppActCo")
        resp = client.post("/opportunities", json={
            "company_id": company["id"],
            "title": "Recent Opportunity",
            "description": "Test",
            "external_url": "https://example.com/1",
            "source": "manual",
            "captured_at": "2026-01-01T00:00:00Z",
        }, headers=operator_a_headers)
        assert resp.status_code == 200, f"Failed to create opportunity: {resp.text}"

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        opp_activities = [a for a in data["recent_activities"] if a["type"] == "opportunity"]
        assert len(opp_activities) >= 1
        assert any("Recent Opportunity" in a["title"] for a in opp_activities)

    def test_recent_activities_sorted_by_date(self, client, admin_headers, operator_a_headers):
        """Recent activities are sorted by created_at descending."""
        company = self._create_company(client, admin_headers, "SortActCo")
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Older Lead",
            "phone": "5511999999998",
            "source": "manual",
        }, headers=operator_a_headers)
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Newer Lead",
            "phone": "5511999999997",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        activities = data["recent_activities"]
        if len(activities) >= 2:
            for i in range(len(activities) - 1):
                assert activities[i]["created_at"] >= activities[i + 1]["created_at"]

    def test_recent_activities_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Recent activities are isolated by tenant."""
        company_a = self._create_company(client, admin_headers, "TenantA")
        self._create_company(client, admin_headers, "TenantB")
        client.post("/leads", json={
            "company_id": company_a["id"],
            "name": "Secret Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_b_headers)
        data = response.json()
        for activity in data["recent_activities"]:
            assert "Secret Lead" not in activity.get("title", "")

    def test_recent_activities_has_created_at(self, client, admin_headers, operator_a_headers):
        """Each activity has a created_at field."""
        company = self._create_company(client, admin_headers, "TimeActCo")
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Time Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        for activity in data["recent_activities"]:
            assert "created_at" in activity
            assert "T" in activity["created_at"]  # ISO format check

    def test_recent_activities_has_type(self, client, admin_headers, operator_a_headers):
        """Each activity has a type field."""
        company = self._create_company(client, admin_headers, "TypeActCo")
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Type Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        for activity in data["recent_activities"]:
            assert activity["type"] in ("opportunity", "conversation", "lead")

    def test_recent_activities_has_title(self, client, admin_headers, operator_a_headers):
        """Each activity has a title field."""
        company = self._create_company(client, admin_headers, "TitleActCo")
        client.post("/leads", json={
            "company_id": company["id"],
            "name": "Title Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        for activity in data["recent_activities"]:
            assert "title" in activity
            assert len(activity["title"]) > 0

    def test_recent_activities_limited_to_20(self, client, admin_headers, operator_a_headers):
        """Recent activities are limited to 20 items max."""
        company = self._create_company(client, admin_headers, "LimitActCo")
        for i in range(25):
            client.post("/leads", json={
                "company_id": company["id"],
                "name": f"Lead {i}",
                "phone": f"551199999999{i:03d}",
                "source": "manual",
            }, headers=operator_a_headers)

        response = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        data = response.json()
        assert len(data["recent_activities"]) <= 20

    def test_recent_activities_requires_auth(self, client, admin_headers):
        """Dashboard with recent activities requires authentication."""
        response = client.get("/internal-tasks/dashboard")
        assert response.status_code == 401

    def test_recent_activities_ui_section_exists(self, client, admin_headers, operator_a_headers):
        """The UI HTML contains the recent activities section."""
        response = client.get("/operator")
        assert response.status_code == 200
        assert "recent-activities-section" in response.text
        assert "recent-activities-list" in response.text
        assert "Atividades recentes" in response.text
