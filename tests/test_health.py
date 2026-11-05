def test_health_is_public_and_stable(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "business-automation"}


def test_healthz_alias_preserves_liveness_contract(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "business-automation"}
