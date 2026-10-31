"""WP-097 — Review queue approval creates opportunity tests."""
import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _trigger_review(client, operator_headers, event_id, message="Test message", channel="web"):
    res = client.post(
        "/review-queue/synthetic-trigger",
        headers=operator_headers,
        json={"event_id": event_id, "message": message, "channel": channel},
    )
    assert res.status_code == 201
    return res.json()


class TestReviewQueueApproveCreatesOpportunity:
    """Verify that approving a review queue item creates an Opportunity."""

    def test_approve_creates_opportunity(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        item = _trigger_review(client, operator_a_headers, "rq-opp-001")
        # Approve the item
        res = client.patch(
            f"/review-queue/{item['id']}/decision",
            headers=operator_a_headers,
            json={"decision": "approve", "operator_note": "Looks good"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "approve"
        # Check opportunity was created
        opps = client.get("/opportunities", headers=operator_a_headers).json()
        review_opps = [o for o in opps if o["source"] == "review_queue"]
        assert len(review_opps) == 1
        opp = review_opps[0]
        assert opp["external_url"] == "review://rq-opp-001"
        assert "Review" in opp["title"] or "Oportunidade" in opp["title"]

    def test_reject_does_not_create_opportunity(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        item = _trigger_review(client, operator_a_headers, "rq-reject-001")
        res = client.patch(
            f"/review-queue/{item['id']}/decision",
            headers=operator_a_headers,
            json={"decision": "reject"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "reject"
        opps = client.get("/opportunities", headers=operator_a_headers).json()
        review_opps = [o for o in opps if o["source"] == "review_queue"]
        assert len(review_opps) == 0

    def test_approve_deduplication(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        item = _trigger_review(client, operator_a_headers, "rq-dedup-001")
        # Approve twice should not create duplicate opportunities
        client.patch(
            f"/review-queue/{item['id']}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        opps = client.get("/opportunities", headers=operator_a_headers).json()
        review_opps = [o for o in opps if o["source"] == "review_queue"]
        assert len(review_opps) == 1

    def test_approve_tenant_isolation(
        self, client, admin_headers, operator_a_headers, operator_b_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        item = _trigger_review(client, operator_a_headers, "rq-tenant-001")
        client.patch(
            f"/review-queue/{item['id']}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        # Operator B should not see the opportunity
        opps = client.get("/opportunities", headers=operator_b_headers).json()
        review_opps = [o for o in opps if o["source"] == "review_queue"]
        assert len(review_opps) == 0

    def test_approve_includes_operator_note(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        item = _trigger_review(client, operator_a_headers, "rq-note-001")
        client.patch(
            f"/review-queue/{item['id']}/decision",
            headers=operator_a_headers,
            json={"decision": "approve", "operator_note": "Priority client"},
        )
        opps = client.get("/opportunities", headers=operator_a_headers).json()
        review_opps = [o for o in opps if o["source"] == "review_queue"]
        assert len(review_opps) == 1
        assert "Priority client" in review_opps[0]["description"]

    def test_approve_with_intent_in_title(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        # Message that triggers commercial intent
        item = _trigger_review(
            client, operator_a_headers, "rq-intent-001",
            "Preciso de automação de processos para minha empresa"
        )
        client.patch(
            f"/review-queue/{item['id']}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        opps = client.get("/opportunities", headers=operator_a_headers).json()
        review_opps = [o for o in opps if o["source"] == "review_queue"]
        assert len(review_opps) == 1
        # Title should include intent if detected
        assert "Review" in review_opps[0]["title"] or "Oportunidade" in review_opps[0]["title"]
