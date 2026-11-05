def test_readiness_reports_database_availability(client):
    response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "business-automation"}


def test_readyz_alias_preserves_readiness_contract(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "business-automation"}
