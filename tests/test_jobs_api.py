# tests for Job Queue API endpoints

import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_jobs():
    response = client.get("/jobs/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_nonexistent_job_error():
    response = client.get("/jobs/nonexistent-id/error")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Job not found"
