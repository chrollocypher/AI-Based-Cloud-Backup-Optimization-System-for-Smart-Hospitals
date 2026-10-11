import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory
from app.models.record import RecordCreate
from app.models.enums import StorageTier
from app.services.record_service import record_service
from app.services.storage_service import storage_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db_memory.clear()
    yield
    db_memory.clear()


def test_storage_tier_transition_routine():
    """Verify standard record tier transition from HOT (Standard) to WARM (Standard-IA)."""
    rec_in = RecordCreate(
        record_id="REC_ROUTINE_01",
        record_type="Billing",
        department="Administrative",
        data_size_mb=40.0,
        access_frequency=2,
        storage_tier=StorageTier.STANDARD
    )
    record_service.create_record(rec_in)

    response = client.post("/api/v1/storage/tier-transitions", json={
        "record_id": "REC_ROUTINE_01",
        "target_tier": "WARM",
        "reason": "Administrative monthly review completed"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["previous_tier"] == "STANDARD"
    assert data["new_tier"] == "STANDARD_IA"
    assert data["aws_storage_class"] == "STANDARD_IA"
    assert "s3://smart-hospital-ehr/standard_ia/billing/REC_ROUTINE_01.json" in data["s3_location"]
    assert data["safety_rule_applied"] is False


def test_clinical_safety_guardrail_interception():
    """Verify that clinical safety rules intercept unsafe archiving of CRITICAL records to Glacier."""
    rec_in = RecordCreate(
        record_id="REC_EMERGENCY_CRIT",
        record_type="Emergency EHR",
        department="Emergency Trauma",
        data_size_mb=35.0,
        access_frequency=25,
        storage_tier=StorageTier.STANDARD,
        emergency_flag=True
    )
    created = record_service.create_record(rec_in)
    assert created.criticality == "CRITICAL"

    # Attempt to move critical emergency record to COLD / Glacier
    response = client.post("/api/v1/storage/tier-transitions", json={
        "record_id": "REC_EMERGENCY_CRIT",
        "target_tier": "COLD",
        "reason": "Accidental archival request"
    })
    assert response.status_code == 200
    data = response.json()

    # Safety guardrail must intercept and clamp to STANDARD_IA (WARM) to satisfy emergency SLAs
    assert data["new_tier"] == "STANDARD_IA"
    assert data["safety_rule_applied"] is True

    # Confirm database reflects the clamped tier
    saved_rec = record_service.get_record("REC_EMERGENCY_CRIT")
    assert saved_rec.storage_tier == "STANDARD_IA"


def test_non_critical_record_allowed_glacier():
    """Verify that non-critical, non-emergency records can transition to Glacier."""
    rec_in = RecordCreate(
        record_id="REC_OLD_ARCHIVE",
        record_type="Administrative",
        department="Billing",
        data_size_mb=150.0,
        access_frequency=0,
        storage_tier=StorageTier.STANDARD
    )
    record_service.create_record(rec_in)

    response = client.post("/api/v1/storage/tier-transitions", json={
        "record_id": "REC_OLD_ARCHIVE",
        "target_tier": "COLD",
        "reason": "Year-end financial compliance archival"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["new_tier"] == "GLACIER"
    assert data["safety_rule_applied"] is False


def test_storage_cost_evaluation():
    """Verify monthly cost calculation comparing multi-tier proposed policy vs static S3 Standard."""
    # Seed records across tiers
    for i in range(5):
        record_service.create_record(RecordCreate(
            record_id=f"REC_HOT_{i}",
            record_type="Emergency EHR",
            department="Emergency",
            data_size_mb=500.0,
            access_frequency=20,
            storage_tier=StorageTier.STANDARD
        ))

    for i in range(10):
        rec = record_service.create_record(RecordCreate(
            record_id=f"REC_COLD_{i}",
            record_type="Administrative",
            department="Billing",
            data_size_mb=2000.0,
            access_frequency=1,
            storage_tier=StorageTier.STANDARD
        ))
        record_service.update_tier(rec.record_id, "GLACIER")

    response = client.get("/api/v1/storage/cost-estimate?region=us-east-1")
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 15
    assert data["total_volume_gb"] > 0
    assert data["static_standard_monthly_cost_usd"] > data["proposed_policy_monthly_cost_usd"]
    assert data["projected_monthly_savings_usd"] > 0
    assert data["savings_percentage"] > 0
    assert len(data["breakdown_by_tier"]) >= 2
    assert data["clinical_safety_protected_count"] == 5


def test_transition_not_found():
    """Verify 404 response for invalid record ID."""
    response = client.post("/api/v1/storage/tier-transitions", json={
        "record_id": "NON_EXISTENT_999",
        "target_tier": "WARM"
    })
    assert response.status_code == 404
