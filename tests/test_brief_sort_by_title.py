"""WP-262: Test brief sorting by opportunity title."""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, operator_headers, company_id, title):
    from datetime import datetime, timezone
    data = {
        "company_id": company_id,
        "title": title,
        "description": "Test description",
        "source": "manual",
        "external_url": f"https://example.com/{title.lower().replace(' ', '-')}",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    res = client.post("/opportunities", headers=operator_headers, json=data)
    assert res.status_code == 200
    return res.json()


def _create_brief(client, operator_headers, opportunity_id):
    # Set opportunity to prepare_proposal status first via triage endpoint
    client.patch(
        f"/opportunities/{opportunity_id}/triage",
        headers=operator_headers,
        json={"next_action": "prepare_proposal"},
    )
    data = {
        "offer_reference": "REF-001",
        "diagnosis": "Test diagnosis",
        "scope": "Test scope",
        "deliverables": "Test deliverables",
        "acceptance_criteria": "Test criteria",
    }
    res = client.post(
        f"/opportunities/{opportunity_id}/proposal-brief",
        headers=operator_headers,
        json=data,
    )
    assert res.status_code == 200
    return res.json()


class TestBriefSortByTitle:
    """Verify GET /proposal-briefs?sort=title sorting."""

    def test_sort_by_title_ascending(self, client, admin_headers, operator_a_headers):
        """Briefs sorted by opportunity title should return alphabetical order."""
        _create_company(client, admin_headers, "Alpha")
        opp_z = _create_opportunity(client, operator_a_headers, 1, "Zebra Project")
        opp_a = _create_opportunity(client, operator_a_headers, 1, "Alpha Project")
        opp_m = _create_opportunity(client, operator_a_headers, 1, "Middle Project")

        _create_brief(client, operator_a_headers, opp_z["id"])
        _create_brief(client, operator_a_headers, opp_a["id"])
        _create_brief(client, operator_a_headers, opp_m["id"])

        res = client.get("/proposal-briefs?sort=title", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) == 3
        assert briefs[0]["opportunity_title"] == "Alpha Project"
        assert briefs[1]["opportunity_title"] == "Middle Project"
        assert briefs[2]["opportunity_title"] == "Zebra Project"

    def test_sort_by_title_with_status_filter(self, client, admin_headers, operator_a_headers):
        """Title sort works with status filter."""
        _create_company(client, admin_headers, "Alpha")
        opp_a = _create_opportunity(client, operator_a_headers, 1, "Alpha Project")
        opp_z = _create_opportunity(client, operator_a_headers, 1, "Zebra Project")

        brief_a = _create_brief(client, operator_a_headers, opp_a["id"])
        _create_brief(client, operator_a_headers, opp_z["id"])

        # Update brief_a status via the opportunity/brief endpoint
        client.patch(
            f"/opportunities/{opp_a['id']}/proposal-brief",
            headers=operator_a_headers,
            json={"status": "ready_for_review"},
        )

        res = client.get(
            "/proposal-briefs?sort=title&status=ready_for_review",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) >= 1
        assert any(b["opportunity_title"] == "Alpha Project" for b in briefs)

    def test_sort_by_title_with_search(self, client, admin_headers, operator_a_headers):
        """Title sort works with keyword search."""
        _create_company(client, admin_headers, "Alpha")
        opp_a = _create_opportunity(client, operator_a_headers, 1, "Alpha Project")
        opp_m = _create_opportunity(client, operator_a_headers, 1, "Middle Project")

        _create_brief(client, operator_a_headers, opp_a["id"])
        _create_brief(client, operator_a_headers, opp_m["id"])

        res = client.get("/proposal-briefs?sort=title&q=project", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) == 2
        assert briefs[0]["opportunity_title"] == "Alpha Project"
        assert briefs[1]["opportunity_title"] == "Middle Project"

    def test_sort_by_title_respects_pagination(self, client, admin_headers, operator_a_headers):
        """Title sort respects limit/offset."""
        _create_company(client, admin_headers, "Alpha")
        opp_z = _create_opportunity(client, operator_a_headers, 1, "Zebra Project")
        opp_a = _create_opportunity(client, operator_a_headers, 1, "Alpha Project")
        opp_m = _create_opportunity(client, operator_a_headers, 1, "Middle Project")

        _create_brief(client, operator_a_headers, opp_z["id"])
        _create_brief(client, operator_a_headers, opp_a["id"])
        _create_brief(client, operator_a_headers, opp_m["id"])

        res = client.get(
            "/proposal-briefs?sort=title&limit=2&offset=1",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        briefs = res.json()
        assert len(briefs) == 2
        assert briefs[0]["opportunity_title"] == "Middle Project"
        assert briefs[1]["opportunity_title"] == "Zebra Project"

    def test_sort_by_title_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Title sort returns only tenant briefs."""
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        opp_a = _create_opportunity(client, operator_a_headers, 1, "Alpha Project")
        opp_b = _create_opportunity(client, operator_b_headers, 2, "AAA Project")

        _create_brief(client, operator_a_headers, opp_a["id"])
        _create_brief(client, operator_b_headers, opp_b["id"])

        res = client.get("/proposal-briefs?sort=title", headers=operator_a_headers)
        assert res.status_code == 200
        briefs = res.json()
        titles = [b["opportunity_title"] for b in briefs]
        assert "AAA Project" not in titles
        assert len(briefs) == 1

    def test_sort_by_title_requires_auth(self, client):
        """Title sort requires authentication."""
        res = client.get("/proposal-briefs?sort=title")
        assert res.status_code in (401, 403)
