import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory
from app.services.retrieval_service import ehr_cache
from scripts.seed_data import seed_records
from scripts.teardown_aws_resources import main as teardown_main

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_environment():
    db_memory.clear()
    ehr_cache.clear()
    yield
    db_memory.clear()
    ehr_cache.clear()


def test_complete_end_to_end_system_workflow():
    """Validates the complete research prototype workflow end-to-end:

    1. Seed Synthetic EHR Data
    2. Dual Forecasting Ingestion
    3. Step Functions Workflow Orchestration
    4. Emergency Retrieval & Cache Hit Verification
    5. Storage Cost Evaluation
    6. System Telemetry & 7 Evaluation Metrics Verification
    7. Automated Teardown Verification
    """
    # Step 1: Seed Synthetic EHR Data
    seeded_records = seed_records()
    assert len(seeded_records) == 6

    # Step 2: Query Dual Forecasting
    forecast_resp = client.get("/api/v1/predictions/joint-forecast")
    assert forecast_resp.status_code == 200
    fdata = forecast_resp.json()
    assert "backup_forecast" in fdata
    assert "access_forecast" in fdata
    assert fdata["workload_intensity_level"] in ["LOW", "NORMAL", "HIGH", "PEAK"]

    # Step 3: Trigger AWS Step Functions Pipeline
    orch_resp = client.post("/api/v1/orchestration/trigger-pipeline")
    assert orch_resp.status_code == 200
    odata = orch_resp.json()
    assert odata["status"] == "SUCCEEDED"
    assert odata["output"]["metrics_result"]["status"] == "COMPLETED"

    # Step 4: Emergency Retrieval & Cache Adherence
    # Emergency record retrieval (First request: Miss)
    ret1 = client.post("/api/v1/retrieval/request", json={
        "record_id": "EHR_10025",
        "is_emergency": True,
        "department": "Emergency Trauma"
    })
    assert ret1.status_code == 200
    d1 = ret1.json()
    assert d1["sla_met"] is True
    assert d1["retrieval_latency_ms"] <= 500.0
    assert d1["cache_hit"] is False

    # Second request: Cache Hit
    ret2 = client.post("/api/v1/retrieval/request", json={
        "record_id": "EHR_10025",
        "is_emergency": True,
        "department": "Emergency Trauma"
    })
    assert ret2.status_code == 200
    d2 = ret2.json()
    assert d2["cache_hit"] is True
    assert d2["retrieval_latency_ms"] < 25.0

    # Step 5: Storage Cost Evaluation
    cost_resp = client.get("/api/v1/storage/cost-estimate?region=us-east-1")
    assert cost_resp.status_code == 200
    cdata = cost_resp.json()
    assert cdata["total_records"] == 6
    assert cdata["clinical_safety_protected_count"] >= 1
    assert "breakdown_by_tier" in cdata

    # Step 6: System Telemetry with all 7 Research Metrics
    telemetry_resp = client.get("/api/v1/monitoring/system-telemetry")
    assert telemetry_resp.status_code == 200
    tdata = telemetry_resp.json()["metrics"]

    assert "1_retrieval_latency" in tdata
    assert "2_critical_record_availability_percent" in tdata
    assert "3_storage_cost" in tdata
    assert "4_cache_hit_rate_percent" in tdata
    assert "5_backup_success_rate_percent" in tdata
    assert "6_sla_violations" in tdata
    assert "7_prediction_accuracy_baseline" in tdata

    assert tdata["2_critical_record_availability_percent"] == 100.0
    assert tdata["4_cache_hit_rate_percent"] == 50.0  # 1 hit out of 2 requests
    assert tdata["6_sla_violations"]["count"] == 0

    # Step 7: Teardown Verification
    td_res = teardown_main(dry_run=True)
    assert td_res["status"] == "SUCCESS"
