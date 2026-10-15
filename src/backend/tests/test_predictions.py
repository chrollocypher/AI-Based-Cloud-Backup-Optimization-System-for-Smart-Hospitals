import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_prediction():
    payload = {
        "data_volume_mb": 8200.0,
        "access_frequency": 530,
        "active_departments": 8
    }
    response = client.post("/api/v1/predictions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_backup_volume_mb" in data
    assert data["forecast_horizon"] == "1 hour"
    assert data["predicted_backup_volume_mb"] > 0.0


def test_get_latest_prediction():
    response = client.get("/api/v1/predictions/latest")
    assert response.status_code == 200
    data = response.json()
    assert "predicted_backup_volume_mb" in data


def test_access_demand_and_joint_forecast_aliases():
    access = client.post("/api/v1/predictions/access-demand", json={
        "current_access_count": 1200,
        "current_access_volume_mb": 15400.0,
        "emergency_context_ratio": 0.05
    })
    assert access.status_code == 200
    body = access.json()
    assert body["predicted_access_count"] > 0
    assert body["predicted_access_volume_mb"] > 0

    joint = client.get("/api/v1/predictions/joint-forecast")
    assert joint.status_code == 200
    j = joint.json()
    assert "backup_forecast" in j
    assert "access_forecast" in j
    assert j["workload_intensity_level"] in ("LOW", "NORMAL", "HIGH", "PEAK")

    alias = client.get("/api/v1/workload/forecast-latest")
    assert alias.status_code == 200
    assert alias.json()["access_forecast"]["predicted_access_count"] > 0
