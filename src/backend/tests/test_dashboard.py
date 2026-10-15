import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_dashboard_data():
    db_memory.clear()
    client.post("/api/v1/records", json={
        "record_id": "EHR_10025",
        "record_type": "EHR",
        "department": "Emergency",
        "data_size_mb": 50.0,
        "access_frequency": 10
    })
    yield
    db_memory.clear()


def test_get_dashboard_summary():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "current_workload_gb" in data
    assert "predicted_workload_gb" in data
    assert data["pending_backups"] == 1
    assert data["critical_pending"] == 1


def test_get_dashboard_workload():
    response = client.get("/api/v1/dashboard/workload")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    assert "actual_gb" in data[0]
    assert "predicted_gb" in data[0]


def test_get_monitoring_status():
    response = client.get("/api/v1/monitoring/status")
    assert response.status_code == 200
    data = response.json()
    assert data["system_status"] == "HEALTHY"
    assert data["database_connected"] is True
    assert data["aws_services_active"] is True
