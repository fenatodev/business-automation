"""Opportunity win rate by source endpoint tests.

Tests the GET /opportunities/win-rate-by-source endpoint that returns
win rate breakdown by opportunity source for the operator dashboard.
"""
from conftest import TestingSessionLocal


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, source="manual", title="Test Opp"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "company_id": company_id,
            "source": source,
            "external_url": f"https://example.com/{title.replace(' ', '-').lower()}-{company_id}",
            "title": title,
            "description": "Test",
            "captured_at": "2026-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200, f"Failed to create opportunity: {res.text}"
    return res.json()


def _close_opportunity(client, headers, opportunity_id, outcome="won", reason="Good deal"):
    res = client.patch(
        f"/opportunities/{opportunity_id}/close",
        headers=headers,
        json={"outcome": outcome, "reason": reason},
    )
    assert res.status_code == 200, f"Failed to close opportunity: {res.text}"
    return res.json()


def test_win_rate_empty_when_no_opportunities(client, admin_headers, operator_a_headers):
    """Returns zeros when no opportunities exist."""
    _create_company(client, admin_headers, name="EmptyCo")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_total"] == 0
    assert data["overall_won"] == 0
    assert data["overall_lost"] == 0
    assert data["overall_win_rate"] == 0.0
    assert data["by_source"] == []


def test_win_rate_excludes_unclosed_opportunities(client, admin_headers, operator_a_headers):
    """Excludes opportunities without outcome won/lost."""
    company = _create_company(client, admin_headers, name="OpenCo")
    _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="Open Opp")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_total"] == 0
    assert data["by_source"] == []


def test_win_rate_single_won(client, admin_headers, operator_a_headers):
    """Returns 100% win rate for single won opportunity."""
    company = _create_company(client, admin_headers, name="WonCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="Won Opp")
    _close_opportunity(client, operator_a_headers, opp["id"], outcome="won")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_total"] == 1
    assert data["overall_won"] == 1
    assert data["overall_lost"] == 0
    assert data["overall_win_rate"] == 100.0
    assert len(data["by_source"]) == 1
    assert data["by_source"][0]["source"] == "manual"
    assert data["by_source"][0]["win_rate"] == 100.0


def test_win_rate_single_lost(client, admin_headers, operator_a_headers):
    """Returns 0% win rate for single lost opportunity."""
    company = _create_company(client, admin_headers, name="LostCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="Lost Opp")
    _close_opportunity(client, operator_a_headers, opp["id"], outcome="lost")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_total"] == 1
    assert data["overall_won"] == 0
    assert data["overall_lost"] == 1
    assert data["overall_win_rate"] == 0.0


def test_win_rate_multiple_sources(client, admin_headers, operator_a_headers):
    """Correctly aggregates by source."""
    company = _create_company(client, admin_headers, name="MultiSourceCo")

    # manual: 2 won, 1 lost => 66.7%
    opp1 = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="M1")
    opp2 = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="M2")
    opp3 = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="M3")
    _close_opportunity(client, operator_a_headers, opp1["id"], outcome="won")
    _close_opportunity(client, operator_a_headers, opp2["id"], outcome="won")
    _close_opportunity(client, operator_a_headers, opp3["id"], outcome="lost")

    # 99freelas: 1 won, 1 lost => 50%
    opp4 = _create_opportunity(client, operator_a_headers, company["id"], source="99freelas", title="F1")
    opp5 = _create_opportunity(client, operator_a_headers, company["id"], source="99freelas", title="F2")
    _close_opportunity(client, operator_a_headers, opp4["id"], outcome="won")
    _close_opportunity(client, operator_a_headers, opp5["id"], outcome="lost")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["overall_total"] == 5
    assert data["overall_won"] == 3
    assert data["overall_lost"] == 2
    assert data["overall_win_rate"] == 60.0

    assert len(data["by_source"]) == 2

    # Find by source
    sources = {item["source"]: item for item in data["by_source"]}
    assert sources["manual"]["total"] == 3
    assert sources["manual"]["won"] == 2
    assert sources["manual"]["lost"] == 1
    assert sources["manual"]["win_rate"] == 66.7

    assert sources["99freelas"]["total"] == 2
    assert sources["99freelas"]["won"] == 1
    assert sources["99freelas"]["lost"] == 1
    assert sources["99freelas"]["win_rate"] == 50.0


def test_win_rate_sorted_by_total_descending(client, admin_headers, operator_a_headers):
    """Results sorted by total descending."""
    company = _create_company(client, admin_headers, name="SortCo")

    # Source A: 1 opportunity
    opp_a = _create_opportunity(client, operator_a_headers, company["id"], source="intake", title="A1")
    _close_opportunity(client, operator_a_headers, opp_a["id"], outcome="won")

    # Source B: 3 opportunities
    for i in range(3):
        opp = _create_opportunity(client, operator_a_headers, company["id"], source="review_queue", title=f"B{i}")
        _close_opportunity(client, operator_a_headers, opp["id"], outcome="won")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["by_source"][0]["source"] == "review_queue"
    assert data["by_source"][0]["total"] == 3
    assert data["by_source"][1]["source"] == "intake"
    assert data["by_source"][1]["total"] == 1


def test_win_rate_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Win rate data is isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    # Create won opportunity for company 2 (operator_b)
    opp_b = _create_opportunity(client, operator_b_headers, 2, source="manual", title="B Opp")
    _close_opportunity(client, operator_b_headers, opp_b["id"], outcome="won")

    # Operator A sees nothing
    res_a = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res_a.status_code == 200
    assert res_a.json()["overall_total"] == 0

    # Operator B sees their own
    res_b = client.get("/opportunities/win-rate-by-source", headers=operator_b_headers)
    assert res_b.status_code == 200
    assert res_b.json()["overall_total"] == 1


def test_win_rate_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/opportunities/win-rate-by-source")
    assert res.status_code == 401


def test_win_rate_response_fields(client, admin_headers, operator_a_headers):
    """Response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="Test")
    _close_opportunity(client, operator_a_headers, opp["id"], outcome="won")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    # Top-level fields
    assert "by_source" in data
    assert "overall_total" in data
    assert "overall_won" in data
    assert "overall_lost" in data
    assert "overall_win_rate" in data

    # Item fields
    item = data["by_source"][0]
    assert "source" in item
    assert "total" in item
    assert "won" in item
    assert "lost" in item
    assert "win_rate" in item


def test_win_rate_mixed_outcomes(client, admin_headers, operator_a_headers):
    """Correctly calculates win rate with mixed outcomes."""
    company = _create_company(client, admin_headers, name="MixedCo")

    # 3 won, 2 lost => 60%
    for i in range(3):
        opp = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title=f"W{i}")
        _close_opportunity(client, operator_a_headers, opp["id"], outcome="won")

    for i in range(2):
        opp = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title=f"L{i}")
        _close_opportunity(client, operator_a_headers, opp["id"], outcome="lost")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_win_rate"] == 60.0


def test_win_rate_with_open_opportunities(client, admin_headers, operator_a_headers):
    """Open opportunities don't affect win rate calculation."""
    company = _create_company(client, admin_headers, name="OpenMixedCo")

    # 1 won (closed)
    opp_won = _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="Won")
    _close_opportunity(client, operator_a_headers, opp_won["id"], outcome="won")

    # 1 open (not closed)
    _create_opportunity(client, operator_a_headers, company["id"], source="manual", title="Open")

    res = client.get("/opportunities/win-rate-by-source", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_total"] == 1
    assert data["overall_won"] == 1
    assert data["overall_win_rate"] == 100.0
