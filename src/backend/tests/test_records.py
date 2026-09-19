import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    db_memory.clear()
    yield
    db_memory.clear()


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_record_emergency_critical():
    payload = {
        "record_id": "EHR_10025",
        "record_type": "EHR",
        "department": "Emergency",
        "data_size_mb": 25.4,
        "access_frequency": 18,
        "timestamp": "2026-09-19T10:15:00Z"
    }
    response = client.post("/api/v1/records", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["record_id"] == "EHR_10025"
    assert data["criticality"] == "CRITICAL"
    assert data["backup_status"] == "PENDING"


def test_create_record_ct_high():
    payload = {
        "record_id": "CT_20041",
        "record_type": "CT",
        "department": "Radiology",
        "data_size_mb": 450.0,
        "access_frequency": 12,
        "timestamp": "2026-09-19T10:30:00Z"
    }
    response = client.post("/api/v1/records", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["criticality"] == "HIGH"


def test_create_record_duplicate_error():
    payload = {
        "record_id": "EHR_10025",
        "record_type": "EHR",
        "department": "Emergency",
        "data_size_mb": 25.4,
        "access_frequency": 18,
        "timestamp": "2026-09-19T10:15:00Z"
    }
    client.post("/api/v1/records", json=payload)
    response = client.post("/api/v1/records", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_and_get_records():
    r1 = {
        "record_id": "REC_1",
        "record_type": "EHR",
        "department": "Emergency",
        "data_size_mb": 10.0,
        "access_frequency": 5,
        "timestamp": "2026-09-19T10:00:00Z"
    }
    r2 = {
        "record_id": "REC_2",
        "record_type": "Administrative",
        "department": "Billing",
        "data_size_mb": 2.0,
        "access_frequency": 1,
        "timestamp": "2026-09-19T10:05:00Z"
    }
    client.post("/api/v1/records", json=r1)
    client.post("/api/v1/records", json=r2)

    list_resp = client.get("/api/v1/records")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    get_resp = client.get("/api/v1/records/REC_1")
    assert get_resp.status_code == 200
    assert get_resp.json()["record_id"] == "REC_1"


def test_get_nonexistent_record():
    response = client.get("/api/v1/records/NONEXISTENT")
    assert response.status_code == 404
