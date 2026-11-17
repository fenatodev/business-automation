"""Opportunity reactivation suggestions endpoint tests.

Tests the GET /opportunities/reactivation-suggestions endpoint that
identifies lost opportunities eligible for re-engagement.
"""
from datetime import datetime, timedelta, timezone

from conftest import TestingSessionLocal


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp", budget=None):
    payload = {
        "source": "manual",
        "external_url": f"https://example.com/{title}",
        "title": title,
        "description": "Test",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if budget is not None:
        payload["budget"] = budget
    res = client.post(
        "/opportunities",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    return res.json()


def _close_as_lost(client, headers, opp_id, reason=None):
    payload = {"outcome": "lost"}
    if reason:
        payload["reason"] = reason
    res = client.patch(
        f"/opportunities/{opp_id}/close",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    return res.json()


def _backdate_closed_at(opp_id, days_ago):
    """Set closed_at to `days_ago` days ago for a lost opportunity."""
    from sqlalchemy import text

    closed_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    with TestingSessionLocal() as db:
        db.execute(
            text("UPDATE opportunities SET closed_at = :ca WHERE id = :id"),
            {"ca": closed_at, "id": opp_id},
        )
        db.commit()


def test_reactivation_empty_when_no_lost_opportunities(
    client, admin_headers, operator_a_headers
):
    """Empty response when no lost opportunities exist."""
    _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["suggestions"] == []
    assert data["total_count"] == 0


def test_reactivation_returns_old_lost_opportunities(
    client, admin_headers, operator_a_headers
):
    """Returns lost opportunities older than min_days (default 30)."""
    _create_company(client, admin_headers, name="OldCo")
    opp = _create_opportunity(
        client, operator_a_headers, title="Old Lost Deal", budget="R$ 5000"
    )
    _close_as_lost(client, operator_a_headers, opp["id"])
    _backdate_closed_at(opp["id"], 45)

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    assert data["suggestions"][0]["id"] == opp["id"]
    assert data["suggestions"][0]["title"] == "Old Lost Deal"
    assert data["suggestions"][0]["budget"] == "R$ 5000"
    assert data["suggestions"][0]["days_since_lost"] >= 44


def test_reactivation_excludes_recently_lost(
    client, admin_headers, operator_a_headers
):
    """Excludes opportunities lost less than min_days ago."""
    _create_company(client, admin_headers, name="RecentCo")
    opp = _create_opportunity(
        client, operator_a_headers, title="Recent Lost Deal"
    )
    _close_as_lost(client, operator_a_headers, opp["id"], reason="Budget cut")
    _backdate_closed_at(opp["id"], 5)

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 0


def test_reactivation_custom_min_days(
    client, admin_headers, operator_a_headers
):
    """Respects custom min_days parameter."""
    _create_company(client, admin_headers, name="MinDaysCo")
    opp1 = _create_opportunity(client, operator_a_headers, title="10-day Lost")
    opp2 = _create_opportunity(client, operator_a_headers, title="20-day Lost")
    _close_as_lost(client, operator_a_headers, opp1["id"])
    _close_as_lost(client, operator_a_headers, opp2["id"])
    _backdate_closed_at(opp1["id"], 10)
    _backdate_closed_at(opp2["id"], 20)

    # min_days=15 should exclude the 10-day one
    res = client.get(
        "/opportunities/reactivation-suggestions?min_days=15",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    assert data["suggestions"][0]["title"] == "20-day Lost"


def test_reactivation_max_results_limit(
    client, admin_headers, operator_a_headers
):
    """Respects max_results parameter."""
    _create_company(client, admin_headers, name="MaxResCo")
    opps = []
    for i in range(5):
        opp = _create_opportunity(client, operator_a_headers, title=f"Lost Deal {i}")
        _close_as_lost(client, operator_a_headers, opp["id"])
        _backdate_closed_at(opp["id"], 40 + i)
        opps.append(opp)

    res = client.get(
        "/opportunities/reactivation-suggestions?max_results=2",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 2


def test_reactivation_sorted_by_most_recent_lost_first(
    client, admin_headers, operator_a_headers
):
    """Results sorted by most recently lost first."""
    _create_company(client, admin_headers, name="SortCo")
    opp1 = _create_opportunity(client, operator_a_headers, title="Oldest Lost")
    opp2 = _create_opportunity(client, operator_a_headers, title="Middle Lost")
    opp3 = _create_opportunity(client, operator_a_headers, title="Newest Lost")
    _close_as_lost(client, operator_a_headers, opp1["id"])
    _close_as_lost(client, operator_a_headers, opp2["id"])
    _close_as_lost(client, operator_a_headers, opp3["id"])
    _backdate_closed_at(opp1["id"], 60)
    _backdate_closed_at(opp2["id"], 45)
    _backdate_closed_at(opp3["id"], 35)

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    titles = [s["title"] for s in data["suggestions"]]
    assert titles == ["Newest Lost", "Middle Lost", "Oldest Lost"]


def test_reactivation_includes_all_fields(
    client, admin_headers, operator_a_headers
):
    """Response includes all expected fields."""
    _create_company(client, admin_headers, name="FieldsCo")
    opp = _create_opportunity(
        client, operator_a_headers, title="Full Fields Deal", budget="R$ 10000"
    )
    _close_as_lost(
        client, operator_a_headers, opp["id"], reason="Client went bankrupt"
    )
    _backdate_closed_at(opp["id"], 40)

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    suggestion = data["suggestions"][0]
    assert suggestion["id"] == opp["id"]
    assert suggestion["title"] == "Full Fields Deal"
    assert suggestion["budget"] == "R$ 10000"
    assert suggestion["reason"] == "Client went bankrupt"
    assert suggestion["source"] == "manual"
    assert suggestion["days_since_lost"] >= 39
    assert "closed_at" in suggestion


def test_reactivation_tenant_isolation(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Only returns opportunities from the authenticated tenant."""
    _create_company(client, admin_headers, name="IsoA")
    _create_company(client, admin_headers, name="IsoB")

    opp_a = _create_opportunity(client, operator_a_headers, title="Company A Lost")
    opp_b = _create_opportunity(client, operator_b_headers, title="Company B Lost")
    _close_as_lost(client, operator_a_headers, opp_a["id"])
    _close_as_lost(client, operator_b_headers, opp_b["id"])
    _backdate_closed_at(opp_a["id"], 40)
    _backdate_closed_at(opp_b["id"], 40)

    res_a = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    data_a = res_a.json()
    assert data_a["total_count"] == 1
    assert data_a["suggestions"][0]["title"] == "Company A Lost"

    res_b = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_b_headers,
    )
    data_b = res_b.json()
    assert data_b["total_count"] == 1
    assert data_b["suggestions"][0]["title"] == "Company B Lost"


def test_reactivation_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/opportunities/reactivation-suggestions")
    assert res.status_code in (401, 403)


def test_reactivation_excludes_non_lost_opportunities(
    client, admin_headers, operator_a_headers
):
    """Only includes opportunities with next_action='lost'."""
    _create_company(client, admin_headers, name="NonLostCo")
    _create_opportunity(client, operator_a_headers, title="Pending Deal")

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 0


def test_reactivation_min_days_validation(client, admin_headers, operator_a_headers):
    """Rejects invalid min_days values."""
    _create_company(client, admin_headers, name="ValCo")

    # min_days=0 should be rejected (ge=1)
    res = client.get(
        "/opportunities/reactivation-suggestions?min_days=0",
        headers=operator_a_headers,
    )
    assert res.status_code == 422

    # min_days=4000 should be rejected (le=3650)
    res = client.get(
        "/opportunities/reactivation-suggestions?min_days=4000",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_reactivation_max_results_validation(client, admin_headers, operator_a_headers):
    """Rejects invalid max_results values."""
    _create_company(client, admin_headers, name="ValCo2")

    # max_results=0 should be rejected (ge=1)
    res = client.get(
        "/opportunities/reactivation-suggestions?max_results=0",
        headers=operator_a_headers,
    )
    assert res.status_code == 422

    # max_results=200 should be rejected (le=100)
    res = client.get(
        "/opportunities/reactivation-suggestions?max_results=200",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_reactivation_combined_min_days_and_max_results(
    client, admin_headers, operator_a_headers
):
    """Both min_days and max_results work together."""
    _create_company(client, admin_headers, name="CombinedCo")
    for i in range(5):
        opp = _create_opportunity(client, operator_a_headers, title=f"Combined {i}")
        _close_as_lost(client, operator_a_headers, opp["id"])
        _backdate_closed_at(opp["id"], 35 + i * 10)

    # min_days=50 filters to 2 items (75 and 85 days), max_results=1 limits to 1
    res = client.get(
        "/opportunities/reactivation-suggestions?min_days=50&max_results=1",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    assert data["suggestions"][0]["days_since_lost"] >= 50


def test_reactivation_null_budget_and_reason(
    client, admin_headers, operator_a_headers
):
    """Handles opportunities with null budget and reason gracefully."""
    _create_company(client, admin_headers, name="NullCo")
    opp = _create_opportunity(client, operator_a_headers, title="Null Fields")
    _close_as_lost(client, operator_a_headers, opp["id"])
    _backdate_closed_at(opp["id"], 40)

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 1
    suggestion = data["suggestions"][0]
    assert suggestion["budget"] is None
    assert suggestion["reason"] is None


def test_reactivation_excludes_done_opportunities(
    client, admin_headers, operator_a_headers
):
    """Excludes opportunities closed as 'done' (won)."""
    _create_company(client, admin_headers, name="DoneCo")
    opp = _create_opportunity(client, operator_a_headers, title="Won Deal")
    # Close as won
    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won"},
    )
    assert res.status_code == 200
    _backdate_closed_at(opp["id"], 40)

    res = client.get(
        "/opportunities/reactivation-suggestions",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 0
