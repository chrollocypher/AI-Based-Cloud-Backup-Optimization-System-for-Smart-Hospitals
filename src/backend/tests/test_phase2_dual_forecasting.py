import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.prediction_service import prediction_service

client = TestClient(app)


def test_backup_volume_endpoint():
    """Verify preserved backup volume prediction endpoint."""
    payload = {
        "data_volume_mb": 9500.0,
        "access_frequency": 600,
        "active_departments": 8
    }
    response = client.post("/api/v1/predictions/backup-volume", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_backup_volume_mb" in data
    assert data["predicted_backup_volume_mb"] > 0
    assert data["forecast_horizon"] == "1 hour"
    assert data["confidence_interval_low"] < data["predicted_backup_volume_mb"] < data["confidence_interval_high"]


def test_access_demand_endpoint():
    """Verify independent access-demand forecasting endpoint."""
    payload = {
        "current_access_count": 1400,
        "current_access_volume_mb": 18200.0,
        "recent_access_counts": [1100, 1200, 1250, 1300, 1350, 1400],
        "emergency_context_ratio": 0.08
    }
    response = client.post("/api/v1/predictions/access-demand", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_access_count" in data
    assert "predicted_access_volume_mb" in data
    assert "predicted_emergency_count" in data
    assert data["predicted_access_count"] > 0
    assert data["predicted_access_volume_mb"] > 0
    assert data["predicted_emergency_count"] >= 0
    assert data["confidence_interval_low"] < data["predicted_access_volume_mb"] < data["confidence_interval_high"]


def test_latest_access_prediction():
    """Verify retrieval of latest access demand forecast."""
    response = client.get("/api/v1/predictions/access-demand/latest")
    assert response.status_code == 200
    data = response.json()
    assert "predicted_access_count" in data
    assert "predicted_access_volume_mb" in data


def test_joint_forecast_endpoint():
    """Verify combined joint workload forecast provides dual predictions and recommendations."""
    response = client.get("/api/v1/predictions/joint-forecast")
    assert response.status_code == 200
    data = response.json()

    assert "backup_forecast" in data
    assert "access_forecast" in data
    assert "workload_intensity_level" in data
    assert "recommendation" in data

    assert data["workload_intensity_level"] in ["LOW", "NORMAL", "HIGH", "PEAK"]
    assert len(data["recommendation"]) > 10

    # Ensure backup and access metrics remain separate
    assert "predicted_backup_volume_mb" in data["backup_forecast"]
    assert "predicted_access_count" in data["access_forecast"]
    assert "predicted_access_volume_mb" in data["access_forecast"]


def test_independent_target_separation():
    """Verify that calling access forecasting does not alter the backup volume target."""
    backup_before = prediction_service.get_latest_prediction().predicted_backup_volume_mb

    # Call access prediction multiple times
    for count in [500, 2500, 4000]:
        client.post("/api/v1/predictions/access-demand", json={
            "current_access_count": count,
            "current_access_volume_mb": float(count * 12),
            "emergency_context_ratio": 0.1
        })

    # Backup volume prediction remains stable and separate
    backup_after = prediction_service.get_latest_prediction().predicted_backup_volume_mb
    assert backup_before == backup_after
