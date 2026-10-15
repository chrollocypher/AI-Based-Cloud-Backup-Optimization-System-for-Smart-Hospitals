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
    assert data["predicted_backup_volume_mb"] > 8200.0


def test_get_latest_prediction():
    response = client.get("/api/v1/predictions/latest")
    assert response.status_code == 200
    data = response.json()
    assert "predicted_backup_volume_mb" in data
