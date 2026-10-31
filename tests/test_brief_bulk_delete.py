"""WP-185 — Bulk delete proposal briefs.

Tests that the operator can delete multiple briefs at once
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


class TestBriefBulkDelete:
    """Test POST /proposal-briefs/bulk-delete."""

    def test_bulk_delete(self, client, admin_headers, operator_a_headers):
        """Bulk delete multiple briefs."""
        _create_company(client, admin_headers, name="DeleteCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        brief1 = _create_brief(client, operator_a_headers, opp1["id"])
        brief2 = _create_brief(client, operator_a_headers, opp2["id"])

        res = client.post(
            "/proposal-briefs/bulk-delete",
            headers=operator_a_headers,
            json={"brief_ids": [brief1["id"], brief2["id"]]},
        )
        assert res.status_code == 200
        result = res.json()
        assert result["deleted"] == 2
        assert sorted(result["deleted_ids"]) == sorted([brief1["id"], brief2["id"]])
        assert result["skipped"] == []

    def test_bulk_delete_skips_nonexistent(self, client, admin_headers, operator_a_headers):
        """Non-existent brief IDs are skipped."""
        _create_company(client, admin_headers, name="SkipDelCo")
        opp = _create_opportunity(client, operator_a_headers, title="Test")
        brief = _create_brief(client, operator_a_headers, opp["id"])

        res = client.post(
            "/proposal-briefs/bulk-delete",
            headers=operator_a_headers,
            json={"brief_ids": [brief["id"], 99999]},
        )
        assert res.status_code == 200
        result = res.json()
        assert result["deleted"] == 1
        assert result["deleted_ids"] == [brief["id"]]
        assert result["skipped"] == [99999]

    def test_bulk_delete_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot delete briefs from another tenant."""
        company_a = _create_company(client, admin_headers, name="TenantDelACo")
        company_b = _create_company(client, admin_headers, name="TenantDelBCo")
        opp_b = _create_opportunity(client, operator_b_headers, title="OppB")
        brief_b = _create_brief(client, operator_b_headers, opp_b["id"])

        res = client.post(
            "/proposal-briefs/bulk-delete",
            headers=operator_a_headers,
            json={"brief_ids": [brief_b["id"]]},
        )
        assert res.status_code == 200
        result = res.json()
        assert result["deleted"] == 0
        assert result["skipped"] == [brief_b["id"]]

    def test_bulk_delete_requires_auth(self, client, admin_headers):
        """Bulk delete requires authentication."""
        res = client.post("/proposal-briefs/bulk-delete", json={})
        assert res.status_code in (401, 403)

    def test_bulk_delete_empty_ids_rejected(self, client, admin_headers, operator_a_headers):
        """Empty brief_ids list is rejected."""
        res = client.post(
            "/proposal-briefs/bulk-delete",
            headers=operator_a_headers,
            json={"brief_ids": []},
        )
        assert res.status_code == 422

    def test_bulk_delete_reflects_in_count(self, client, admin_headers, operator_a_headers):
        """Bulk delete is reflected in the count endpoint."""
        _create_company(client, admin_headers, name="CountDelCo")
        opp1 = _create_opportunity(client, operator_a_headers, title="First")
        opp2 = _create_opportunity(client, operator_a_headers, title="Second")
        brief1 = _create_brief(client, operator_a_headers, opp1["id"])
        brief2 = _create_brief(client, operator_a_headers, opp2["id"])

        res = client.get("/proposal-briefs/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] >= 2

        client.post(
            "/proposal-briefs/bulk-delete",
            headers=operator_a_headers,
            json={"brief_ids": [brief1["id"], brief2["id"]]},
        )

        res = client.get("/proposal-briefs/count", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["count"] == 0
