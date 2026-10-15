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
def reset_db_and_cache():
    db_memory.clear()
    ehr_cache.clear()
    yield
    db_memory.clear()
    ehr_cache.clear()


def test_emergency_retrieval_cache_miss_then_hit():
    """Verify that the first retrieval is a cache miss and subsequent retrieval is an ultra-fast cache hit."""
    record_service.create_record(RecordCreate(
        record_id="REC_EMERG_01",
        record_type="Emergency EHR",
        department="Emergency Trauma",
        data_size_mb=15.0,
        access_frequency=10,
        storage_tier=StorageTier.STANDARD,
        emergency_flag=True
    ))

    # 1. First retrieval -> Cache Miss
    resp1 = client.post("/api/v1/retrieval/request", json={
        "record_id": "REC_EMERG_01",
        "is_emergency": True,
        "department": "Emergency",
        "reason": "Trauma intake"
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["cache_hit"] is False
    assert data1["sla_met"] is True
    assert data1["retrieval_latency_ms"] <= 500.0
    assert data1["storage_tier"] == "STANDARD"

    # 2. Second retrieval -> Cache Hit
    resp2 = client.post("/api/v1/retrieval/request", json={
        "record_id": "REC_EMERG_01",
        "is_emergency": True,
        "department": "ICU",
        "reason": "Follow-up monitoring"
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["cache_hit"] is True
    assert data2["sla_met"] is True
    # In-memory cache latency is under 25 ms
    assert data2["retrieval_latency_ms"] < 25.0
    assert data2["retrieval_latency_ms"] < data1["retrieval_latency_ms"]


def test_standard_ia_emergency_retrieval():
    """Verify that retrieval from STANDARD_IA tier satisfies the 500 ms SLA target."""
    rec = record_service.create_record(RecordCreate(
        record_id="REC_WARM_01",
        record_type="EHR",
        department="General Inpatient",
        data_size_mb=45.0,
        access_frequency=3,
        storage_tier=StorageTier.STANDARD
    ))
    record_service.update_tier(rec.record_id, "WARM")

    resp = client.post("/api/v1/retrieval/request", json={
        "record_id": "REC_WARM_01",
        "is_emergency": True,
        "department": "Emergency",
        "reason": "Unexpected critical decompensation"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["storage_tier"] == "STANDARD_IA"
    assert data["cache_hit"] is False
    assert data["sla_met"] is True
    assert data["retrieval_latency_ms"] <= 500.0


def test_glacier_emergency_sla_violation():
    """Verify that attempting emergency retrieval on an archived Glacier object violates the emergency SLA."""
    rec = record_service.create_record(RecordCreate(
        record_id="REC_ARCHIVED_01",
        record_type="Administrative",
        department="Billing",
        data_size_mb=100.0,
        access_frequency=0,
        storage_tier=StorageTier.STANDARD
    ))
    # Directly set to Glacier in DB
    record_service.update_tier(rec.record_id, "GLACIER")

    resp = client.post("/api/v1/retrieval/request", json={
        "record_id": "REC_ARCHIVED_01",
        "is_emergency": True,
        "department": "Emergency",
        "reason": "Emergency forensic clinical check"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["storage_tier"] == "GLACIER"
    # Glacier restore delay severely violates the 500 ms SLA
    assert data["sla_met"] is False
    assert data["retrieval_latency_ms"] > 500.0


def test_prefetching_records():
    """Verify proactive cache prefetching warms the cache."""
    # Create multiple records
    ids = []
    for i in range(3):
        rec = record_service.create_record(RecordCreate(
            record_id=f"REC_PREFETCH_{i}",
            record_type="EHR",
            department="Cardiology",
            data_size_mb=20.0,
            access_frequency=8
        ))
        ids.append(rec.record_id)

    # Prefetch records
    prefetch_resp = client.post("/api/v1/retrieval/prefetch", json={
        "record_ids": ids,
        "reason": "Cardiology clinic batch opening"
    })
    assert prefetch_resp.status_code == 200
    pdata = prefetch_resp.json()
    assert pdata["prefetched_count"] == 3
    assert pdata["failed_count"] == 0

    # Immediate retrieval of prefetched record should be a cache hit
    ret_resp = client.post("/api/v1/retrieval/request", json={
        "record_id": ids[0],
        "is_emergency": False,
        "department": "Cardiology"
    })
    assert ret_resp.status_code == 200
    assert ret_resp.json()["cache_hit"] is True


def test_retrieval_metrics_telemetry():
    """Verify aggregate calculation of hit rate, SLA violations, and latency metrics."""
    # 1. Normal emergency retrieval (Hit after Miss)
    rec = record_service.create_record(RecordCreate(
        record_id="REC_METRIC_01",
        record_type="EHR",
        department="Emergency",
        data_size_mb=10.0,
        access_frequency=5
    ))
    client.post("/api/v1/retrieval/request", json={"record_id": "REC_METRIC_01", "is_emergency": True})
    client.post("/api/v1/retrieval/request", json={"record_id": "REC_METRIC_01", "is_emergency": True})

    # 2. Glacier violation retrieval
    rec_cold = record_service.create_record(RecordCreate(
        record_id="REC_METRIC_02",
        record_type="Administrative",
        department="Billing",
        data_size_mb=10.0,
        access_frequency=0
    ))
    record_service.update_tier(rec_cold.record_id, "GLACIER")
    client.post("/api/v1/retrieval/request", json={"record_id": "REC_METRIC_02", "is_emergency": True})

    metrics_resp = client.get("/api/v1/retrieval/metrics")
    assert metrics_resp.status_code == 200
    mdata = metrics_resp.json()

    assert mdata["total_retrieval_requests"] == 3
    assert mdata["emergency_requests_count"] == 3
    assert mdata["cache_hits_count"] == 1
    assert mdata["cache_hit_rate_percent"] == 33.33
    assert mdata["sla_violations_count"] == 1
    assert mdata["sla_violation_rate_percent"] == 33.33
    assert "STANDARD" in mdata["average_latency_by_tier_ms"]
