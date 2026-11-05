def test_readiness_reports_database_availability(client):
    response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "business-automation"}
