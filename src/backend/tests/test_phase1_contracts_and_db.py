import pytest
from datetime import datetime, timezone
from app.models.enums import (
    StorageTier,
    TierLabel,
    map_tier_label_to_aws_class,
    Criticality,
    AccessType,
    CRITICALITY_WEIGHTS
)
from app.models.access_log import RawAccessEvent, HourlyWorkloadWindow
from app.models.record import RecordCreate, RecordResponse
from app.models.retrieval import EmergencyRetrievalRequest, RetrievalJobResponse
from app.db.dynamodb import db_memory
from app.services.record_service import record_service


def setup_function():
    """Clear in-memory database before every test."""
    db_memory.clear()


def test_storage_tier_mappings():
    """Verify deterministic mapping between business tier labels and AWS S3 storage classes."""
    assert map_tier_label_to_aws_class("HOT") == StorageTier.STANDARD
    assert map_tier_label_to_aws_class("WARM") == StorageTier.STANDARD_IA
    assert map_tier_label_to_aws_class("COLD") == StorageTier.GLACIER_FLEXIBLE
    assert map_tier_label_to_aws_class("ARCHIVE") == StorageTier.GLACIER_DEEP_ARCHIVE

    # Case-insensitivity check
    assert map_tier_label_to_aws_class("hot") == StorageTier.STANDARD
    assert map_tier_label_to_aws_class("standard") == StorageTier.STANDARD

    with pytest.raises(ValueError):
        map_tier_label_to_aws_class("NON_EXISTENT_TIER")


def test_criticality_weights():
    """Verify documented 4-level criticality hierarchy."""
    assert CRITICALITY_WEIGHTS[Criticality.CRITICAL.value] == 4
    assert CRITICALITY_WEIGHTS[Criticality.HIGH.value] == 3
    assert CRITICALITY_WEIGHTS[Criticality.MEDIUM.value] == 2
    assert CRITICALITY_WEIGHTS[Criticality.LOW.value] == 1


def test_raw_access_event_schema_validation():
    """Validate raw access-event schema containing all 12 required fields."""
    event = RawAccessEvent(
        event_id="EVT_9901",
        timestamp=datetime.now(timezone.utc),
        patient_id="P_SYN_001",
        record_type="EHR",
        department="Emergency",
        access_type=AccessType.RETRIEVE,
        access_frequency=12,
        data_size_mb=18.5,
        criticality=Criticality.CRITICAL,
        storage_tier=StorageTier.STANDARD,
        emergency_flag=True,
        backup_status=None
    )
    assert event.event_id == "EVT_9901"
    assert event.access_type == AccessType.RETRIEVE
    assert event.emergency_flag is True
    assert event.data_size_mb == 18.5


def test_hourly_workload_window_schema():
    """Validate 6-field hourly aggregated workload target."""
    window = HourlyWorkloadWindow(
        window_start_time=datetime.now(timezone.utc),
        access_event_count=120,
        access_volume_mb=4500.0,
        backup_event_count=15,
        backup_volume_mb=980.5,
        emergency_event_count=8
    )
    assert window.access_event_count == 120
    assert window.backup_event_count == 15
    assert window.emergency_event_count == 8


def test_emergency_retrieval_models():
    """Validate emergency retrieval request and SLA tracking models."""
    req = EmergencyRetrievalRequest(
        record_id="REC_200",
        is_emergency=True,
        department="Emergency Trauma",
        reason="Acute trauma imaging"
    )
    assert req.is_emergency is True

    resp = RetrievalJobResponse(
        retrieval_id="RET_001",
        record_id="REC_200",
        is_emergency=True,
        storage_tier=StorageTier.STANDARD,
        cache_hit=True,
        retrieval_latency_ms=25.0,
        sla_target_ms=500.0,
        sla_met=True,
        requested_at=datetime.now(timezone.utc)
    )
    assert resp.sla_met is True
    assert resp.retrieval_latency_ms < resp.sla_target_ms


def test_multi_table_in_memory_persistence():
    """Test multi-table CRUD operations in InMemoryDatabase."""
    # 1. EHR Record
    rec_in = RecordCreate(
        record_id="REC_101",
        patient_id="P_SYN_101",
        record_type="CT",
        department="Radiology",
        data_size_mb=120.0,
        access_frequency=5,
        storage_tier=StorageTier.STANDARD
    )
    created = record_service.create_record(rec_in)
    assert created.record_id == "REC_101"
    assert created.storage_tier == "STANDARD"

    # 2. Update storage tier
    updated = record_service.update_tier("REC_101", "WARM")
    assert updated is not None
    assert updated.storage_tier == "STANDARD_IA"

    # 3. Access Event Logging
    event = RawAccessEvent(
        event_id="EVT_101",
        timestamp=datetime.now(timezone.utc),
        patient_id="P_SYN_101",
        record_type="CT",
        department="Radiology",
        access_type=AccessType.READ,
        access_frequency=6,
        data_size_mb=120.0,
        criticality=Criticality.HIGH,
        storage_tier=StorageTier.STANDARD_IA,
        emergency_flag=False
    )
    record_service.record_access_event(event)

    events = record_service.list_access_events(patient_id="P_SYN_101")
    assert len(events) == 1
    assert events[0]["event_id"] == "EVT_101"

    # 4. Emergency retrieval storage
    retrieval_dict = {
        "retrieval_id": "RET_TEST_1",
        "record_id": "REC_101",
        "is_emergency": True,
        "latency_ms": 45.0,
        "sla_met": True
    }
    db_memory.put_retrieval(retrieval_dict)
    assert db_memory.get_retrieval("RET_TEST_1")["is_emergency"] is True
    assert len(db_memory.list_retrievals(is_emergency=True)) == 1
