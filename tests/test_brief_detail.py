"""WP-187 — Brief detail panel.

Tests that the operator can view a single brief with all fields,
with tenant isolation and proper validation.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp"):
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": "manual",
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_brief(client, headers, opportunity_id):
    res = client.patch(
        f"/opportunities/{opportunity_id}/triage",
        headers=headers,
        json={"next_action": "prepare_proposal"},
    )
    assert res.status_code == 200
    res = client.post(
        f"/opportunities/{opportunity_id}/proposal-brief",
        headers=headers,
        json={
            "offer_reference": f"OFF-{opportunity_id}",
            "diagnosis": "Diagnosis text",
            "scope": "Scope text",
            "deliverables": "Deliverables text",
            "acceptance_criteria": "Acceptance text",
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    return res.json()


class TestBriefDetail:
    """Test GET /proposal-briefs/{id}."""

    def test_get_brief_detail(self, client, admin_headers, operator_a_headers):
        """Get single brief returns all fields."""
        _create_company(client, admin_headers, name="DetailCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        brief = _create_brief(client, operator_a_headers, opp["id"])

        res = client.get(
            f"/proposal-briefs/{brief['id']}",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        result = res.json()
        assert result["id"] == brief["id"]
        assert result["offer_reference"] == brief["offer_reference"]
        assert result["diagnosis"] == "Diagnosis text"
        assert result["scope"] == "Scope text"
        assert result["deliverables"] == "Deliverables text"
        assert result["acceptance_criteria"] == "Acceptance text"
        assert result["status"] == "draft"
        assert result["opportunity_id"] == opp["id"]
        assert result["created_at"] is not None

    def test_get_brief_not_found(self, client, operator_a_headers):
        """Non-existent brief returns 404."""
        res = client.get(
            "/proposal-briefs/99999",
            headers=operator_a_headers,
        )
        assert res.status_code == 404

    def test_get_brief_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot view brief from another tenant."""
        company_a = _create_company(client, admin_headers, name="TenantACo")
        company_b = _create_company(client, admin_headers, name="TenantBCo")

        opp_b = _create_opportunity(client, operator_b_headers, title="OppB")
        brief_b = _create_brief(client, operator_b_headers, opp_b["id"])

        res = client.get(
            f"/proposal-briefs/{brief_b['id']}",
            headers=operator_a_headers,
        )
        assert res.status_code == 404

    def test_get_brief_requires_auth(self, client, admin_headers, operator_a_headers):
        """Get brief requires authentication."""
        res = client.get("/proposal-briefs/1")
        assert res.status_code in (401, 403)

    def test_get_brief_after_status_change(self, client, admin_headers, operator_a_headers):
        """Brief detail reflects status changes."""
        _create_company(client, admin_headers, name="StatusCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        brief = _create_brief(client, operator_a_headers, opp["id"])

        # Change status to ready_for_review
        client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief["id"]],
                "status": "ready_for_review",
            },
        )

        res = client.get(
            f"/proposal-briefs/{brief['id']}",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        result = res.json()
        assert result["status"] == "ready_for_review"
