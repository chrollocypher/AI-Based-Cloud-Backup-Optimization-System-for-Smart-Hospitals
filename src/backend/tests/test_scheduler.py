import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_records():
    db_memory.clear()
    # Seed 1 critical, 1 low record
    client.post("/api/v1/records", json={
        "record_id": "EHR_1001",
        "record_type": "EHR",
        "department": "Emergency",
        "data_size_mb": 50.0,
        "access_frequency": 20
    })
    client.post("/api/v1/records", json={
        "record_id": "ADMIN_9001",
        "record_type": "Administrative",
        "department": "Billing",
        "data_size_mb": 5.0,
        "access_frequency": 1
    })
    yield
    db_memory.clear()


def test_generate_and_get_schedule():
    resp = client.post("/api/v1/schedule")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pending_records"] == 2
    assert len(data["schedule"]) == 2

    # Check that critical EHR is prioritized over admin
    assert data["schedule"][0]["record_id"] == "EHR_1001"
    assert data["schedule"][0]["criticality"] == "CRITICAL"

    get_resp = client.get("/api/v1/schedule")
    assert get_resp.status_code == 200
    assert get_resp.json()["total_pending_records"] == 2
