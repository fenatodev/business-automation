"""WP-059: tenant-isolated review queue status counters."""
from tests.test_commercial_pipeline_e2e import _synthetic_trigger


def test_summary_empty(client, operator_a_headers):
    response = client.get("/review-queue/summary", headers=operator_a_headers)
    assert response.status_code == 200
    assert response.json() == {"pending": 0, "approve": 0, "reject": 0}


def test_summary_tenant_isolation_and_decision(client, admin_headers, operator_a_headers, operator_b_headers):
    for id_, name in ((1, "Summary A"), (2, "Summary B")):
        response = client.post("/companies", json={"name": name, "slug": "summary-" + str(id_)}, headers=admin_headers)
        assert response.status_code == 200
    first = client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id="summary-a"), headers=operator_a_headers)
    second = client.post("/review-queue/synthetic-trigger", json=_synthetic_trigger(event_id="summary-b"), headers=operator_b_headers)
    assert first.status_code == second.status_code == 201
    assert client.get("/review-queue/summary", headers=operator_a_headers).json()["pending"] == 1
    assert client.get("/review-queue/summary", headers=operator_b_headers).json()["pending"] == 1
    decision = client.patch(f"/review-queue/{first.json()['id']}/decision", json={"decision": "approve"}, headers=operator_a_headers)
    assert decision.status_code == 200
    assert client.get("/review-queue/summary", headers=operator_a_headers).json() == {"pending": 0, "approve": 1, "reject": 0}
    assert client.get("/review-queue/summary", headers=operator_b_headers).json() == {"pending": 1, "approve": 0, "reject": 0}


def test_summary_requires_operator(client):
    assert client.get("/review-queue/summary").status_code == 401
