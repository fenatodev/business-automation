"""WP-513 — Opportunity close with reason and final value."""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp"):
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": "99freelas",
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Close as won ---


def test_close_opportunity_won(client, admin_headers, operator_a_headers):
    """Closing as won sets outcome, closed_at, and next_action=done."""
    _create_company(client, admin_headers, name="WonCo")
    opp = _create_opportunity(client, operator_a_headers, title="WonOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won", "reason": "Client signed", "final_value": "R$ 15.000"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "won"
    assert data["reason"] == "Client signed"
    assert data["final_value"] == "R$ 15.000"
    assert data["closed_at"] is not None
    assert data["next_action"] == "done"


def test_close_opportunity_won_minimal(client, admin_headers, operator_a_headers):
    """Closing as won with only outcome works."""
    _create_company(client, admin_headers, name="WonMinCo")
    opp = _create_opportunity(client, operator_a_headers, title="WonMinOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "won"
    assert data["closed_at"] is not None
    assert data["next_action"] == "done"


# --- Close as lost ---


def test_close_opportunity_lost(client, admin_headers, operator_a_headers):
    """Closing as lost sets outcome, closed_at, and next_action=lost."""
    _create_company(client, admin_headers, name="LostCo")
    opp = _create_opportunity(client, operator_a_headers, title="LostOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "lost", "reason": "Budget cut"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "lost"
    assert data["reason"] == "Budget cut"
    assert data["closed_at"] is not None
    assert data["next_action"] == "lost"


# --- Validation ---


def test_close_already_closed(client, admin_headers, operator_a_headers):
    """Closing an already closed opportunity returns 400."""
    _create_company(client, admin_headers, name="AlreadyCo")
    opp = _create_opportunity(client, operator_a_headers, title="AlreadyOpp")

    client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won"},
    )

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "lost", "reason": "Changed mind"},
    )
    assert res.status_code == 400


def test_close_invalid_outcome(client, admin_headers, operator_a_headers):
    """Invalid outcome value is rejected."""
    _create_company(client, admin_headers, name="InvalidCo")
    opp = _create_opportunity(client, operator_a_headers, title="InvalidOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "pending"},
    )
    assert res.status_code == 422


def test_close_requires_outcome(client, admin_headers, operator_a_headers):
    """Closing without outcome is rejected."""
    _create_company(client, admin_headers, name="NoOutcomeCo")
    opp = _create_opportunity(client, operator_a_headers, title="NoOutcomeOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"reason": "No outcome provided"},
    )
    assert res.status_code == 422


# --- Auth and tenant isolation ---


def test_close_requires_auth(client):
    """Close requires authentication."""
    res = client.patch("/opportunities/999/close", json={"outcome": "won"})
    assert res.status_code in (401, 403)


def test_close_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot close Operator B's opportunity."""
    _create_company(client, admin_headers, name="CloseIsoA")
    _create_company(client, admin_headers, name="CloseIsoB")

    opp_b = _create_opportunity(client, operator_b_headers, title="CloseIsoBOpp")

    res = client.patch(
        f"/opportunities/{opp_b['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won"},
    )
    assert res.status_code == 404


# --- Reason and final_value length ---


def test_close_reason_max_length(client, admin_headers, operator_a_headers):
    """Reason exceeding max_length is rejected."""
    _create_company(client, admin_headers, name="LongReasonCo")
    opp = _create_opportunity(client, operator_a_headers, title="LongReasonOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won", "reason": "x" * 2001},
    )
    assert res.status_code == 422


def test_close_final_value_max_length(client, admin_headers, operator_a_headers):
    """Final value exceeding max_length is rejected."""
    _create_company(client, admin_headers, name="LongValueCo")
    opp = _create_opportunity(client, operator_a_headers, title="LongValueOpp")

    res = client.patch(
        f"/opportunities/{opp['id']}/close",
        headers=operator_a_headers,
        json={"outcome": "won", "final_value": "x" * 121},
    )
    assert res.status_code == 422
