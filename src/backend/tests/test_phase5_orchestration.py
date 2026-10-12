import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory
from app.models.record import RecordCreate
from app.models.enums import StorageTier
from app.services.record_service import record_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    db_memory.clear()
    yield
    db_memory.clear()


def test_trigger_storage_pipeline_end_to_end():
    """Verify that triggering the pipeline executes the full state machine:

    Forecast -> Decide Tiers -> Execute S3 Transitions -> Publish Metrics.
    """
    # Seed records: 1 critical emergency record, 1 high-access record, 1 inactive record
    record_service.create_record(RecordCreate(
        record_id="REC_ORCH_CRIT",
        record_type="Emergency EHR",
        department="Emergency Trauma",
        data_size_mb=25.0,
        access_frequency=15,
        storage_tier=StorageTier.STANDARD,
        emergency_flag=True
    ))

    record_service.create_record(RecordCreate(
        record_id="REC_ORCH_WARM",
        record_type="CT",
        department="Radiology",
        data_size_mb=80.0,
        access_frequency=4,
        storage_tier=StorageTier.STANDARD
    ))

    record_service.create_record(RecordCreate(
        record_id="REC_ORCH_COLD",
        record_type="Administrative",
        department="Billing",
        data_size_mb=120.0,
        access_frequency=0,
        storage_tier=StorageTier.STANDARD
    ))

    # Trigger Step Functions pipeline
    response = client.post("/api/v1/orchestration/trigger-pipeline")
    assert response.status_code == 200
    data = response.json()

    assert "execution_id" in data
    assert data["status"] == "SUCCEEDED"
    assert "output" in data

    output = data["output"]
    assert "forecast" in output
    assert "decisions" in output
    assert "transitions_result" in output
    assert "metrics_result" in output

    # Verify decisions
    decisions = output["decisions"]["decisions"]
    crit_dec = next(d for d in decisions if d["record_id"] == "REC_ORCH_CRIT")
    assert crit_dec["target_tier"] == "STANDARD"  # Clinical safety maintained

    cold_dec = next(d for d in decisions if d["record_id"] == "REC_ORCH_COLD")
    assert cold_dec["target_tier"] == "GLACIER"  # Inactive moved to cold tier

    # Verify S3 transitions executed
    assert output["transitions_result"]["transitions_executed_count"] >= 1

    # Verify record in DB is now in GLACIER
    updated_rec = record_service.get_record("REC_ORCH_COLD")
    assert updated_rec.storage_tier == "GLACIER"


def test_get_execution_details():
    """Verify retrieval of execution trace by ID."""
    trigger_resp = client.post("/api/v1/orchestration/trigger-pipeline")
    exec_id = trigger_resp.json()["execution_id"]

    get_resp = client.get(f"/api/v1/orchestration/executions/{exec_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["execution_id"] == exec_id


def test_list_executions():
    """Verify listing all pipeline runs."""
    client.post("/api/v1/orchestration/trigger-pipeline")
    client.post("/api/v1/orchestration/trigger-pipeline")

    list_resp = client.get("/api/v1/orchestration/executions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 2
