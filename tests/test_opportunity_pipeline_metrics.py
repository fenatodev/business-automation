"""Opportunity pipeline metrics endpoint tests.

Tests the GET /opportunities/pipeline-metrics endpoint that returns
opportunities grouped by next_action stage for the operator dashboard.
"""
from datetime import datetime, timezone

from conftest import TestingSessionLocal


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, company_id, title="Opp", source="manual", external_url="http://example.com/1"):
    res = client.post(
        "/opportunities",
        headers=headers,
        json={
            "company_id": company_id,
            "source": source,
            "external_url": external_url,
            "title": title,
            "description": "Test opportunity",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


def _triage_opportunity(client, headers, opportunity_id, next_action, triage_note=None):
    payload = {"next_action": next_action}
    if triage_note:
        payload["triage_note"] = triage_note
    res = client.patch(
        f"/opportunities/{opportunity_id}/triage",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    return res.json()


def _close_opportunity(client, headers, opportunity_id, outcome, reason=None, final_value=None):
    payload = {"outcome": outcome}
    if reason:
        payload["reason"] = reason
    if final_value:
        payload["final_value"] = final_value
    res = client.patch(
        f"/opportunities/{opportunity_id}/close",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    return res.json()


def test_pipeline_metrics_empty_when_no_opportunities(
    client, admin_headers, operator_a_headers
):
    """Returns zeros when no opportunities exist."""
    _create_company(client, admin_headers, name="EmptyCo")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_opportunities"] == 0
    assert data["stages"] == []
    assert data["won_count"] == 0
    assert data["lost_count"] == 0
    assert data["win_rate"] == 0.0


def test_pipeline_metrics_single_stage(
    client, admin_headers, operator_a_headers
):
    """Returns correct count for a single stage."""
    company = _create_company(client, admin_headers, name="SingleCo")
    opp1 = _create_opportunity(client, operator_a_headers, company["id"], title="Opp 1", external_url="http://example.com/1")
    opp2 = _create_opportunity(client, operator_a_headers, company["id"], title="Opp 2", external_url="http://example.com/2")
    _triage_opportunity(client, operator_a_headers, opp1["id"], "follow")
    # opp2 stays pending

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_opportunities"] == 2

    stages = {s["stage"]: s["count"] for s in data["stages"]}
    assert stages["pending"] == 1
    assert stages["follow"] == 1


def test_pipeline_metrics_multiple_stages(
    client, admin_headers, operator_a_headers
):
    """Returns correct counts for multiple stages."""
    company = _create_company(client, admin_headers, name="MultiCo")

    opps = []
    for i in range(5):
        opps.append(_create_opportunity(
            client, operator_a_headers, company["id"],
            title=f"Opp {i}", external_url=f"http://example.com/{i}"
        ))

    # Use stages reachable from pending via valid transitions
    # pending → follow → prepare_proposal → in_progress → done/lost
    _triage_opportunity(client, operator_a_headers, opps[1]["id"], "follow")
    _triage_opportunity(client, operator_a_headers, opps[2]["id"], "follow")
    _triage_opportunity(client, operator_a_headers, opps[2]["id"], "prepare_proposal")
    _triage_opportunity(client, operator_a_headers, opps[3]["id"], "follow")
    _triage_opportunity(client, operator_a_headers, opps[3]["id"], "prepare_proposal")
    _triage_opportunity(client, operator_a_headers, opps[3]["id"], "in_progress")
    # opps[4] stays pending

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_opportunities"] == 5

    stage_counts = {s["stage"]: s["count"] for s in data["stages"]}
    assert stage_counts["pending"] == 2  # opps 0, 4
    assert stage_counts["follow"] == 1   # opp 1
    assert stage_counts["prepare_proposal"] == 1  # opp 2
    assert stage_counts["in_progress"] == 1  # opp 3


def test_pipeline_metrics_stage_order(
    client, admin_headers, operator_a_headers
):
    """Stages are returned in a consistent order."""
    company = _create_company(client, admin_headers, name="OrderCo")

    opps = []
    for i in range(3):
        opps.append(_create_opportunity(
            client, operator_a_headers, company["id"],
            title=f"Opp {i}", external_url=f"http://example.com/{i}"
        ))

    _triage_opportunity(client, operator_a_headers, opps[0]["id"], "in_progress")
    _triage_opportunity(client, operator_a_headers, opps[1]["id"], "follow")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    data = res.json()
    stage_names = [s["stage"] for s in data["stages"]]

    # pending should come before follow, follow before in_progress
    assert stage_names.index("pending") < stage_names.index("follow")
    assert stage_names.index("follow") < stage_names.index("in_progress")


def test_pipeline_metrics_won_lost_count(
    client, admin_headers, operator_a_headers
):
    """Correctly counts won and lost opportunities."""
    company = _create_company(client, admin_headers, name="WonLostCo")

    opp1 = _create_opportunity(client, operator_a_headers, company["id"], title="Won Opp", external_url="http://example.com/1")
    opp2 = _create_opportunity(client, operator_a_headers, company["id"], title="Lost Opp", external_url="http://example.com/2")
    opp3 = _create_opportunity(client, operator_a_headers, company["id"], title="Open Opp", external_url="http://example.com/3")

    _close_opportunity(client, operator_a_headers, opp1["id"], "won")
    _close_opportunity(client, operator_a_headers, opp2["id"], "lost")
    # opp3 remains open

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["won_count"] == 1
    assert data["lost_count"] == 1
    assert data["total_opportunities"] == 3


def test_pipeline_metrics_win_rate(
    client, admin_headers, operator_a_headers
):
    """Calculates win rate correctly."""
    company = _create_company(client, admin_headers, name="WinRateCo")

    opps = []
    for i in range(5):
        opps.append(_create_opportunity(
            client, operator_a_headers, company["id"],
            title=f"Opp {i}", external_url=f"http://example.com/{i}"
        ))

    # 3 won, 2 lost => 60% win rate
    for i in range(3):
        _close_opportunity(client, operator_a_headers, opps[i]["id"], "won")
    for i in range(3, 5):
        _close_opportunity(client, operator_a_headers, opps[i]["id"], "lost")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["win_rate"] == 60.0


def test_pipeline_metrics_win_rate_zero_when_no_closed(
    client, admin_headers, operator_a_headers
):
    """Win rate is 0.0 when no opportunities are closed."""
    company = _create_company(client, admin_headers, name="NoClosedCo")
    _create_opportunity(client, operator_a_headers, company["id"], title="Open", external_url="http://example.com/1")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["win_rate"] == 0.0
    assert data["won_count"] == 0
    assert data["lost_count"] == 0


def test_pipeline_metrics_win_rate_100_percent(
    client, admin_headers, operator_a_headers
):
    """Win rate is 100% when all closed are won."""
    company = _create_company(client, admin_headers, name="AllWonCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], title="Won", external_url="http://example.com/1")
    _close_opportunity(client, operator_a_headers, opp["id"], "won")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["win_rate"] == 100.0


def test_pipeline_metrics_tenant_isolation(
    client, admin_headers, operator_a_headers, operator_b_headers
):
    """Only returns metrics for the authenticated tenant."""
    company_a = _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")

    for i in range(3):
        _create_opportunity(
            client, operator_a_headers, company_a["id"],
            title=f"A Opp {i}", external_url=f"http://a.com/{i}"
        )
    for i in range(5):
        _create_opportunity(
            client, operator_b_headers, company_b["id"],
            title=f"B Opp {i}", external_url=f"http://b.com/{i}"
        )

    res_a = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    data_a = res_a.json()
    assert data_a["total_opportunities"] == 3

    res_b = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_b_headers,
    )
    data_b = res_b.json()
    assert data_b["total_opportunities"] == 5


def test_pipeline_metrics_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/opportunities/pipeline-metrics")
    assert res.status_code in (401, 403)


def test_pipeline_metrics_response_fields(
    client, admin_headers, operator_a_headers
):
    """Response includes all expected fields with correct types."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    opp = _create_opportunity(client, operator_a_headers, company["id"], title="Opp", external_url="http://example.com/1")
    _triage_opportunity(client, operator_a_headers, opp["id"], "follow")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_opportunities" in data
    assert "stages" in data
    assert "won_count" in data
    assert "lost_count" in data
    assert "win_rate" in data
    assert isinstance(data["total_opportunities"], int)
    assert isinstance(data["stages"], list)
    assert isinstance(data["won_count"], int)
    assert isinstance(data["lost_count"], int)
    assert isinstance(data["win_rate"], (int, float))

    # Check stage structure
    for stage in data["stages"]:
        assert "stage" in stage
        assert "count" in stage
        assert isinstance(stage["stage"], str)
        assert isinstance(stage["count"], int)


def test_pipeline_metrics_skips_empty_stages(
    client, admin_headers, operator_a_headers
):
    """Only returns stages that have opportunities."""
    company = _create_company(client, admin_headers, name="SparseCo")
    opp1 = _create_opportunity(client, operator_a_headers, company["id"], title="Opp 1", external_url="http://example.com/1")
    opp2 = _create_opportunity(client, operator_a_headers, company["id"], title="Opp 2", external_url="http://example.com/2")
    _triage_opportunity(client, operator_a_headers, opp2["id"], "follow")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    data = res.json()
    stage_names = [s["stage"] for s in data["stages"]]

    # Only pending and follow should appear
    assert "follow" in stage_names
    assert "pending" in stage_names
    assert "prepare_proposal" not in stage_names
    assert "in_progress" not in stage_names


def test_pipeline_metrics_combined_stages_and_outcome(
    client, admin_headers, operator_a_headers
):
    """Stages and won/lost counts work together correctly.
    
    Note: close() changes next_action to 'done' (won) or 'lost' (lost),
    so closed opportunities appear in those stages, not pending.
    """
    company = _create_company(client, admin_headers, name="CombinedCo")

    opps = []
    for i in range(6):
        opps.append(_create_opportunity(
            client, operator_a_headers, company["id"],
            title=f"Opp {i}", external_url=f"http://example.com/{i}"
        ))

    # 1 follow, 1 prepare_proposal
    _triage_opportunity(client, operator_a_headers, opps[2]["id"], "follow")
    _triage_opportunity(client, operator_a_headers, opps[3]["id"], "follow")
    _triage_opportunity(client, operator_a_headers, opps[3]["id"], "prepare_proposal")

    # Close opps[4] as won (next_action → done), opps[5] as lost (next_action → lost)
    _close_opportunity(client, operator_a_headers, opps[4]["id"], "won")
    _close_opportunity(client, operator_a_headers, opps[5]["id"], "lost")

    res = client.get(
        "/opportunities/pipeline-metrics",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total_opportunities"] == 6
    assert data["won_count"] == 1
    assert data["lost_count"] == 1
    assert data["win_rate"] == 50.0

    stage_counts = {s["stage"]: s["count"] for s in data["stages"]}
    # opps 0, 1 stay pending; opp 2 → follow; opp 3 → prepare_proposal
    # opp 4 → done (won), opp 5 → lost (lost)
    assert stage_counts["pending"] == 2
    assert stage_counts["follow"] == 1
    assert stage_counts["prepare_proposal"] == 1
    assert stage_counts["done"] == 1
    assert stage_counts["lost"] == 1
