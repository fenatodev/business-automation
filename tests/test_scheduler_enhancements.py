# Tests for Scheduler enhancements

import time
from fastapi.testclient import TestClient
from app.main import app
from app.services.scheduler import scheduler

client = TestClient(app)

def test_start_stop_scheduler():
    # Ensure scheduler is stopped initially
    scheduler.stop()
    # Start
    resp = client.post("/scheduler/start")
    assert resp.status_code == 200
    assert resp.json() is True
    # Starting again should return False
    resp2 = client.post("/scheduler/start")
    assert resp2.status_code == 200
    assert resp2.json() is False
    # Stop
    resp3 = client.post("/scheduler/stop")
    assert resp3.status_code == 200
    assert resp3.json() is True
    # Stopping again should return False
    resp4 = client.post("/scheduler/stop")
    assert resp4.status_code == 200
    assert resp4.json() is False
