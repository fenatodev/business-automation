"""WP-184 — Bulk status update for proposal briefs.

Tests that the operator can update the status of multiple briefs at once
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
            "diagnosis": "Diagnosis",
            "scope": "Scope",
            "deliverables": "Deliverables",
            "acceptance_criteria": "Acceptance",
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    return res.json()


class TestBriefBulkStatus:
    """Test POST /proposal-briefs/bulk-status."""

    def test_bulk_update_to_ready_for_review(self, client, admin_headers, operator_a_headers):
        """Bulk update multiple briefs to ready_for_review."""
        _create_company(client, admin_headers, name="BulkCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        brief1 = _create_brief(client, operator_a_headers, opp1["id"])
        brief2 = _create_brief(client, operator_a_headers, opp2["id"])

        res = client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief1["id"], brief2["id"]],
                "status": "ready_for_review",
            },
        )
        assert res.status_code == 200
        result = res.json()
        assert result["updated"] == 2
        assert sorted(result["updated_ids"]) == sorted([brief1["id"], brief2["id"]])
        assert result["skipped"] == []

    def test_bulk_update_to_draft(self, client, admin_headers, operator_a_headers):
        """Bulk update briefs back to draft."""
        _create_company(client, admin_headers, name="DraftCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        brief1 = _create_brief(client, operator_a_headers, opp1["id"])
        brief2 = _create_brief(client, operator_a_headers, opp2["id"])

        # First set to ready_for_review
        client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief1["id"], brief2["id"]],
                "status": "ready_for_review",
            },
        )

        # Then set back to draft
        res = client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief1["id"], brief2["id"]],
                "status": "draft",
            },
        )
        assert res.status_code == 200
        result = res.json()
        assert result["updated"] == 2

    def test_bulk_update_skips_nonexistent(self, client, admin_headers, operator_a_headers):
        """Non-existent brief IDs are skipped."""
        _create_company(client, admin_headers, name="SkipCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        brief = _create_brief(client, operator_a_headers, opp["id"])

        res = client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief["id"], 99999, 88888],
                "status": "ready_for_review",
            },
        )
        assert res.status_code == 200
        result = res.json()
        assert result["updated"] == 1
        assert result["updated_ids"] == [brief["id"]]
        assert sorted(result["skipped"]) == [88888, 99999]

    def test_bulk_update_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot update briefs from another tenant."""
        company_a = _create_company(client, admin_headers, name="TenantACo")
        company_b = _create_company(client, admin_headers, name="TenantBCo")

        opp_a = _create_opportunity(client, operator_a_headers, title="OppA")
        brief_a = _create_brief(client, operator_a_headers, opp_a["id"])

        opp_b = _create_opportunity(client, operator_b_headers, title="OppB")
        brief_b = _create_brief(client, operator_b_headers, opp_b["id"])

        # Operator A tries to update brief B
        res = client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief_b["id"]],
                "status": "ready_for_review",
            },
        )
        assert res.status_code == 200
        result = res.json()
        assert result["updated"] == 0
        assert result["skipped"] == [brief_b["id"]]

    def test_bulk_update_requires_auth(self, client, admin_headers, operator_a_headers):
        """Bulk update requires authentication."""
        res = client.post("/proposal-briefs/bulk-status", json={})
        assert res.status_code in (401, 403)

    def test_bulk_update_invalid_status(self, client, admin_headers, operator_a_headers):
        """Invalid status is rejected."""
        _create_company(client, admin_headers, name="InvalidCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        brief = _create_brief(client, operator_a_headers, opp["id"])

        res = client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief["id"]],
                "status": "approved",
            },
        )
        assert res.status_code == 422

    def test_bulk_update_empty_ids_rejected(self, client, admin_headers, operator_a_headers):
        """Empty brief_ids list is rejected."""
        res = client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [],
                "status": "draft",
            },
        )
        assert res.status_code == 422

    def test_bulk_update_reflects_in_list(self, client, admin_headers, operator_a_headers):
        """Bulk update is reflected in the list endpoint."""
        _create_company(client, admin_headers, name="ReflectCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        brief1 = _create_brief(client, operator_a_headers, opp1["id"])
        brief2 = _create_brief(client, operator_a_headers, opp2["id"])

        # Update both to ready_for_review
        client.post(
            "/proposal-briefs/bulk-status",
            headers=operator_a_headers,
            json={
                "brief_ids": [brief1["id"], brief2["id"]],
                "status": "ready_for_review",
            },
        )

        # Verify via list endpoint
        res = client.get(
            "/proposal-briefs?status=ready_for_review",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 2
        assert all(b["status"] == "ready_for_review" for b in briefs)
