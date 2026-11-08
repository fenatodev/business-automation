"""WP-084 / WP-512 — Approve and reject proposal brief endpoints with operator feedback."""
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


# --- WP-512: operator_note and decided_at ---


def test_approve_with_operator_note(client, admin_headers, operator_a_headers):
    """Approving with operator_note persists the note and sets decided_at."""
    _create_company(client, admin_headers, name="NoteCo")
    opp = _create_opportunity(client, operator_a_headers, title="NoteOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/approve",
        headers=operator_a_headers,
        json={"decision": "approve", "operator_note": "Looks good, proceed."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["operator_note"] == "Looks good, proceed."
    assert data["decided_at"] is not None


def test_approve_without_note(client, admin_headers, operator_a_headers):
    """Approving without body still works; decided_at is set."""
    _create_company(client, admin_headers, name="NoNoteCo")
    opp = _create_opportunity(client, operator_a_headers, title="NoNoteOpp")
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
    assert data["decided_at"] is not None


def test_reject_with_operator_note(client, admin_headers, operator_a_headers):
    """Rejecting with operator_note persists the note and sets decided_at."""
    _create_company(client, admin_headers, name="RejectNoteCo")
    opp = _create_opportunity(client, operator_a_headers, title="RejectNoteOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/opportunities/{opp['id']}/proposal-brief/reject",
        headers=operator_a_headers,
        json={"decision": "reject", "operator_note": "Needs revision."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "draft"
    assert data["operator_note"] == "Needs revision."
    assert data["decided_at"] is not None


# --- WP-512: unified decision endpoint ---


def test_decision_approve(client, admin_headers, operator_a_headers):
    """Unified decision endpoint approves a ready_for_review brief."""
    _create_company(client, admin_headers, name="DecApproveCo")
    opp = _create_opportunity(client, operator_a_headers, title="DecApproveOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    brief = _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/proposal-briefs/{brief['id']}/decision",
        headers=operator_a_headers,
        json={"decision": "approve", "operator_note": "Approved via decision endpoint"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["operator_note"] == "Approved via decision endpoint"
    assert data["decided_at"] is not None

    # Opportunity should be advanced
    res = client.get(f"/opportunities/{opp['id']}", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["next_action"] == "in_progress"


def test_decision_reject(client, admin_headers, operator_a_headers):
    """Unified decision endpoint rejects a ready_for_review brief."""
    _create_company(client, admin_headers, name="DecRejectCo")
    opp = _create_opportunity(client, operator_a_headers, title="DecRejectOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    brief = _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/proposal-briefs/{brief['id']}/decision",
        headers=operator_a_headers,
        json={"decision": "reject", "operator_note": "Rejected via decision endpoint"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "draft"
    assert data["operator_note"] == "Rejected via decision endpoint"
    assert data["decided_at"] is not None


def test_decision_approve_draft_fails(client, admin_headers, operator_a_headers):
    """Decision approve on a draft brief returns 400."""
    _create_company(client, admin_headers, name="DecDraftCo")
    opp = _create_opportunity(client, operator_a_headers, title="DecDraftOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    brief = _create_brief(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/proposal-briefs/{brief['id']}/decision",
        headers=operator_a_headers,
        json={"decision": "approve"},
    )
    assert res.status_code == 400


def test_decision_reject_draft_fails(client, admin_headers, operator_a_headers):
    """Decision reject on a draft brief returns 400."""
    _create_company(client, admin_headers, name="DecRjDraftCo")
    opp = _create_opportunity(client, operator_a_headers, title="DecRjDraftOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    brief = _create_brief(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/proposal-briefs/{brief['id']}/decision",
        headers=operator_a_headers,
        json={"decision": "reject"},
    )
    assert res.status_code == 400


def test_decision_not_found(client, operator_a_headers):
    """Decision on non-existent brief returns 404."""
    res = client.patch(
        "/proposal-briefs/99999/decision",
        headers=operator_a_headers,
        json={"decision": "approve"},
    )
    assert res.status_code == 404


def test_decision_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot decide on Operator B's brief."""
    _create_company(client, admin_headers, name="DecIsoA")
    _create_company(client, admin_headers, name="DecIsoB")

    opp_b = _create_opportunity(client, operator_b_headers, title="DecIsoBOpp")
    _triage_to_prepare(client, operator_b_headers, opp_b["id"])
    brief_b = _create_brief(client, operator_b_headers, opp_b["id"])
    _set_brief_ready(client, operator_b_headers, opp_b["id"])

    res = client.patch(
        f"/proposal-briefs/{brief_b['id']}/decision",
        headers=operator_a_headers,
        json={"decision": "approve"},
    )
    assert res.status_code == 404


def test_decision_without_note(client, admin_headers, operator_a_headers):
    """Decision without operator_note still works."""
    _create_company(client, admin_headers, name="DecNoNoteCo")
    opp = _create_opportunity(client, operator_a_headers, title="DecNoNoteOpp")
    _triage_to_prepare(client, operator_a_headers, opp["id"])
    brief = _create_brief(client, operator_a_headers, opp["id"])
    _set_brief_ready(client, operator_a_headers, opp["id"])

    res = client.patch(
        f"/proposal-briefs/{brief['id']}/decision",
        headers=operator_a_headers,
        json={"decision": "approve"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["decided_at"] is not None


def test_decision_requires_auth(client):
    """Decision endpoint requires authentication."""
    res = client.patch("/proposal-briefs/999/decision", json={"decision": "approve"})
    assert res.status_code in (401, 403)
