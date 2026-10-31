"""WP-084 — Approve and reject proposal brief endpoints."""
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


def _triage_to_prepare(client, headers, opp_id):
    res = client.patch(
        f"/opportunities/{opp_id}/triage", headers=headers,
        json={"next_action": "prepare_proposal"},
    )
    assert res.status_code == 200
    return res.json()


def _create_brief(client, headers, opp_id):
    res = client.post(
        f"/opportunities/{opp_id}/proposal-brief", headers=headers,
        json={
            "offer_reference": "test-offer",
            "diagnosis": "Test diagnosis",
            "scope": "Test scope",
            "deliverables": "Test deliverables",
            "acceptance_criteria": "Test criteria",
        },
    )
    assert res.status_code == 200
    return res.json()


def _set_brief_ready(client, headers, opp_id):
    res = client.patch(
        f"/opportunities/{opp_id}/proposal-brief", headers=headers,
        json={
            "offer_reference": "test-offer",
            "diagnosis": "Test diagnosis",
            "scope": "Test scope",
            "deliverables": "Test deliverables",
            "acceptance_criteria": "Test criteria",
            "status": "ready_for_review",
        },
    )
    assert res.status_code == 200
    return res.json()


# --- Approve tests ---


def test_approve_brief_success(client, admin_headers, operator_a_headers):
    """Approving a ready_for_review brief works and advances opportunity."""
    _create_company(client, admin_headers, name="ApproveCo")
    opp = _create_opportunity(client, operator_a_headers, title="ApproveOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/approve",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"

    # Opportunity should be advanced to in_progress
    res = client.get(f"/opportunities/{opp['id']}", headers=operator_a_headers)
    assert res.status_code == 200
    opp_data = res.json()
    assert opp_data["next_action"] == "in_progress"


def test_approve_brief_rejects_draft(client, admin_headers, operator_a_headers):
    """Approving a draft brief returns 400."""
    _create_company(client, admin_headers, name="DraftCo")
    opp = _create_opportunity(client, operator_a_headers, title="DraftOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/approve",
        headers=operator_a_headers,
    )
    assert res.status_code == 400


def test_approve_brief_double_approve(client, admin_headers, operator_a_headers):
    """Approving an already approved brief returns 400."""
    _create_company(client, admin_headers, name="DoubleCo")
    opp = _create_opportunity(client, operator_a_headers, title="DoubleOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/approve",
        headers=operator_a_headers,
    )

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/approve",
        headers=operator_a_headers,
    )
    assert res.status_code == 400


def test_approve_brief_requires_auth(client):
    """Approve requires authentication."""
    res = client.patch("/opportunities/999/proposal-brief/approve")
    assert res.status_code in (401, 403)


# --- Reject tests ---


def test_reject_ready_for_review(client, admin_headers, operator_a_headers):
    """Rejecting a ready_for_review brief reverts it to draft."""
    _create_company(client, admin_headers, name="RejectRfrCo")
    opp = _create_opportunity(client, operator_a_headers, title="RejectRfrOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/reject",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "draft"


def test_reject_approved(client, admin_headers, operator_a_headers):
    """Rejecting an approved brief reverts it to draft."""
    _create_company(client, admin_headers, name="RejectAppCo")
    opp = _create_opportunity(client, operator_a_headers, title="RejectAppOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    # First approve
    client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/approve",
        headers=operator_a_headers,
    )

    # Then reject
    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/reject",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "draft"


def test_reject_draft_fails(client, admin_headers, operator_a_headers):
    """Rejecting a draft brief returns 400."""
    _create_company(client, admin_headers, name="RejectDraftCo")
    opp = _create_opportunity(client, operator_a_headers, title="RejectDraftOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/reject",
        headers=operator_a_headers,
    )
    assert res.status_code == 400


def test_reject_requires_auth(client):
    """Reject requires authentication."""
    res = client.patch("/opportunities/999/proposal-brief/reject")
    assert res.status_code in (401, 403)


def test_reject_does_not_change_opportunity(client, admin_headers, operator_a_headers):
    """Rejecting a ready_for_review brief does not change opportunity next_action."""
    _create_company(client, admin_headers, name="RejectNoChangeCo")
    opp = _create_opportunity(client, operator_a_headers, title="RejectNoChangeOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/reject",
        headers=operator_a_headers,
    )
    assert res.status_code == 200

    res = client.get(f"/opportunities/{opp['id']}", headers=operator_a_headers)
    assert res.status_code == 200
    opp_data = res.json()
    assert opp_data["next_action"] == "prepare_proposal"


def test_approve_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot approve Operator B's brief."""
    _create_company(client, admin_headers, name="IsoA")
    _create_company(client, admin_headers, name="IsoB")

    opp_b = _create_opportunity(client, operator_b_headers, title="IsoBOpp")
    _triage_to_prepare(client, operator_b_headers, opp_b["id"])
    _create_brief(client, operator_b_headers, opp_b["id"])
    _set_brief_ready(client, operator_b_headers, opp_b["id"])

    res = client.patch(
        f"/opportunities/{opp_b['id']}/proposal-brief/approve",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_reject_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot reject Operator B's brief."""
    _create_company(client, admin_headers, name="IsoRA")
    _create_company(client, admin_headers, name="IsoRB")

    opp_b = _create_opportunity(client, operator_b_headers, title="IsoRBOpp")
    _triage_to_prepare(client, operator_b_headers, opp_b["id"])
    _create_brief(client, operator_b_headers, opp_b["id"])
    _set_brief_ready(client, operator_b_headers, opp_b["id"])

    res = client.patch(
        f"/opportunities/{opp_b['id']}/proposal-brief/reject",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
