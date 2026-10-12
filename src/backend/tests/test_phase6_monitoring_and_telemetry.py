import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory
from app.models.record import RecordCreate
from app.models.enums import StorageTier
from app.services.record_service import record_service
from app.services.retrieval_service import ehr_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_environment():
    db_memory.clear()
    ehr_cache.clear()
    yield
    db_memory.clear()
    ehr_cache.clear()


def test_system_telemetry_seven_metrics():
    """Verify that system telemetry returns all 7 research evaluation metrics."""
    # Seed data
    rec = record_service.create_record(RecordCreate(
        record_id="REC_MON_01",
        record_type="Emergency EHR",
        department="Emergency",
        data_size_mb=30.0,
        access_frequency=5,
        storage_tier=StorageTier.STANDARD,
        emergency_flag=True
    ))

    # Perform a retrieval
    client.post("/api/v1/retrieval/request", json={
        "record_id": rec.record_id,
        "is_emergency": True
    })

    response = client.get("/api/v1/monitoring/system-telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data

    m = data["metrics"]
    # Check all 7 metrics:
    assert "1_retrieval_latency" in m
    assert "2_critical_record_availability_percent" in m
    assert "3_storage_cost" in m
    assert "4_cache_hit_rate_percent" in m
    assert "5_backup_success_rate_percent" in m
    assert "6_sla_violations" in m
    assert "7_prediction_accuracy_baseline" in m

    assert m["2_critical_record_availability_percent"] == 100.0
    assert m["6_sla_violations"]["count"] == 0


def test_publish_cloudwatch_metrics():
    """Verify custom CloudWatch metrics publication endpoint."""
    response = client.post("/api/v1/monitoring/cloudwatch/publish")
    assert response.status_code == 200
    data = response.json()

    assert data["namespace"] == "SmartHospital/EHRStorage"
    assert data["metric_count"] == 5
    metric_names = [item["MetricName"] for item in data["metrics"]]
    assert "EmergencyRetrievalLatency" in metric_names
    assert "CacheHitRate" in metric_names
    assert "SLAViolationsCount" in metric_names
    assert "BackupSuccessRate" in metric_names
    assert "EstimatedMonthlySavingsUSD" in metric_names


def test_cloudwatch_alarm_state_transitions():
    """Verify CloudWatch alarms transition from OK to ALARM on clinical SLA violation."""
    # 1. Initially without violations, SLA alarm should be OK
    initial_alarms = client.get("/api/v1/monitoring/cloudwatch/alarms").json()
    sla_alarm = next(a for a in initial_alarms if a["alarm_name"] == "EHR_Emergency_SLA_Violation_Alarm")
    assert sla_alarm["state"] == "OK"

    # 2. Trigger an SLA violation by retrieving a cold Glacier record under emergency
    cold_rec = record_service.create_record(RecordCreate(
        record_id="REC_COLD_ALARM",
        record_type="Billing",
        department="Finance",
        data_size_mb=50.0,
        access_frequency=0,
        storage_tier=StorageTier.STANDARD
    ))
    record_service.update_tier(cold_rec.record_id, "GLACIER")
    client.post("/api/v1/retrieval/request", json={
        "record_id": cold_rec.record_id,
        "is_emergency": True
    })

    # 3. Check alarms: Emergency SLA alarm must be ALARM
    triggered_alarms = client.get("/api/v1/monitoring/cloudwatch/alarms").json()
    triggered_sla = next(a for a in triggered_alarms if a["alarm_name"] == "EHR_Emergency_SLA_Violation_Alarm")
    assert triggered_sla["state"] == "ALARM"
    assert triggered_sla["current_value"] >= 1
    assert "SNS" in triggered_sla["action"]
