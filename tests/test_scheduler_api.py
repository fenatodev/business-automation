# tests for Scheduler API endpoints

import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
OPERATOR_A_TOKEN = "test-operator-a-token-not-a-real-secret"
operator_a_headers = {"Authorization": f"Bearer {OPERATOR_A_TOKEN}"}

def test_list_scheduled_jobs():
    response = client.get("/scheduler/", headers=operator_a_headers)
    assert response.status_code == 200
    # Should return a list (maybe empty)
    assert isinstance(response.json(), list)

def test_cancel_nonexistent_job():
    # Try to cancel a job that likely does not exist
    response = client.patch("/scheduler/nonexistent-id/cancel", headers=operator_a_headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Scheduled job nonexistent-id not found"
