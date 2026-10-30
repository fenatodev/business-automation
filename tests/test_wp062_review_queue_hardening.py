"""WP-062: bounded review queue pagination and conditional decisions."""
from tests.test_commercial_pipeline_e2e import _synthetic_trigger


def _company(client, admin_headers):
    assert client.post("/companies", json={"name": "Hardening A", "slug": "hardening-a"}, headers=admin_headers).status_code == 200
    assert client.post("/companies", json={"name": "Hardening B", "slug": "hardening-b"}, headers=admin_headers).status_code == 200


def test_bounded_pagination(client, admin_headers, operator_a_headers, operator_b_headers):
    _company(client, admin_headers)
    for index in range(4):
        response = client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id=f"wp062-a-{index}"), headers=operator_a_headers)
        assert response.status_code == 201
    assert client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id="wp062-b"), headers=operator_b_headers).status_code == 201
    first = client.get("/review-queue/?limit=2", headers=operator_a_headers)
    second = client.get("/review-queue/?limit=2&offset=2", headers=operator_a_headers)
    assert first.status_code == second.status_code == 200
    ids = [x["id"] for x in first.json() + second.json()]
    assert len(ids) == len(set(ids)) == 4
    assert client.get("/review-queue/?limit=101", headers=operator_a_headers).status_code == 422
    assert client.get("/review-queue/?offset=-1", headers=operator_a_headers).status_code == 422
    assert len(client.get("/review-queue/", headers=operator_b_headers).json()) == 1


def test_decision_cannot_be_replaced(client, admin_headers, operator_a_headers):
    _company(client, admin_headers)
    created = client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id="wp062-decision"), headers=operator_a_headers)
    assert created.status_code == 201
    url = f"/review-queue/{created.json()['id']}/decision"
    first = client.patch(url, json={"decision": "approve", "operator_note": "first"}, headers=operator_a_headers)
    second = client.patch(url, json={"decision": "reject", "operator_note": "second"}, headers=operator_a_headers)
    assert first.status_code == 200
    assert second.status_code == 409
    actual = client.get(f"/review-queue/{created.json()['id']}", headers=operator_a_headers).json()
    assert actual["status"] == "approve"
    assert actual["operator_note"] == "first"
