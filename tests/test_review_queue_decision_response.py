"""WP-098 — Review queue decision returns opportunity_id."""
from datetime import datetime, timezone

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


class TestReviewQueueDecisionResponse:
    """Verify that PATCH /review-queue/{id}/decision returns opportunity_id."""

    def test_approve_returns_opportunity_id(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        # Trigger a synthetic review item
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "whatsapp",
                "message": "Preciso de automação para minha loja",
                "event_id": "rq-decision-test-001",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        # Approve the item
        approve_res = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        assert approve_res.status_code == 200
        data = approve_res.json()
        assert data["status"] == "approve"
        assert "opportunity_id" in data
        assert data["opportunity_id"] is not None

    def test_approve_opportunity_exists_in_list(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Automação de processos",
                "event_id": "rq-decision-test-002",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        approve_res = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        assert approve_res.status_code == 200
        opp_id = approve_res.json()["opportunity_id"]

        # Verify the opportunity appears in the list
        list_res = client.get("/opportunities", headers=operator_a_headers)
        assert list_res.status_code == 200
        opps = list_res.json()
        opp = next((o for o in opps if o["id"] == opp_id), None)
        assert opp is not None
        assert opp["source"] == "review_queue"

    def test_reject_returns_no_opportunity_id(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "email",
                "message": "Não é do meu interesse",
                "event_id": "rq-decision-test-003",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        reject_res = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "reject"},
        )
        assert reject_res.status_code == 200
        data = reject_res.json()
        assert data["status"] == "reject"
        assert data["opportunity_id"] is None

    def test_reject_does_not_create_opportunity(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Test reject",
                "event_id": "rq-decision-test-004",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "reject"},
        )
        # Verify no review_queue opportunity was created
        list_res = client.get("/opportunities", headers=operator_a_headers)
        opps = list_res.json()
        assert not any(o["source"] == "review_queue" for o in opps)

    def test_approve_with_operator_note(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "whatsapp",
                "message": "Preciso de integração ERP",
                "event_id": "rq-decision-test-005",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        approve_res = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "approve", "operator_note": "Cliente prioritário"},
        )
        assert approve_res.status_code == 200
        data = approve_res.json()
        assert data["opportunity_id"] is not None
        assert data["operator_note"] == "Cliente prioritário"

    def test_approve_response_has_item_fields(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "telegram",
                "message": "Automação de marketing",
                "event_id": "rq-decision-test-006",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        approve_res = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        assert approve_res.status_code == 200
        data = approve_res.json()
        # Verify all expected fields are present
        assert "id" in data
        assert "event_id" in data
        assert "channel" in data
        assert "status" in data
        assert "opportunity_id" in data
        assert data["event_id"] == "rq-decision-test-006"
        assert data["channel"] == "telegram"

    def test_approve_requires_auth(self, client):
        res = client.patch(
            "/review-queue/999/decision",
            json={"decision": "approve"},
        )
        assert res.status_code in (401, 403)

    def test_approve_not_found(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.patch(
            "/review-queue/99999/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        assert res.status_code == 404

    def test_approve_already_decided(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Test double approve",
                "event_id": "rq-decision-test-007",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        # First approve
        client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        # Second approve should fail
        res2 = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_a_headers,
            json={"decision": "approve"},
        )
        assert res2.status_code == 409

    def test_approve_tenant_isolation(
        self, client, admin_headers, operator_a_headers, operator_b_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        res = client.post(
            "/review-queue/synthetic-trigger",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Alpha review",
                "event_id": "rq-tenant-test-001",
            },
        )
        assert res.status_code == 201
        item_id = res.json()["id"]

        # Operator B cannot approve Alpha's item
        res_b = client.patch(
            f"/review-queue/{item_id}/decision",
            headers=operator_b_headers,
            json={"decision": "approve"},
        )
        assert res_b.status_code == 404
