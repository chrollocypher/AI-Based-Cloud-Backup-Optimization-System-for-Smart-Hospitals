import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from threading import Lock

from app.models.enums import StorageTier, AccessType, Criticality
from app.models.retrieval import (
    EmergencyRetrievalRequest,
    RetrievalJobResponse,
    PrefetchRequest,
    PrefetchResponse,
    RetrievalMetricsSummary
)
from app.models.access_log import RawAccessEvent
from app.db.dynamodb import db_memory
from app.core.logging import logger
from app.services.record_service import record_service
from app.services.storage_service import storage_service


class EHRRecordCache:
    """Thread-safe fast in-memory cache simulating hot edge cache / Redis for EHR records."""

    def __init__(self, capacity: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._capacity = capacity
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if record_id in self._cache:
                self.hits += 1
                return self._cache[record_id]
            self.misses += 1
            return None

    def put(self, record_id: str, data: Dict[str, Any]):
        with self._lock:
            if len(self._cache) >= self._capacity:
                # Evict oldest entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[record_id] = data

    def contains(self, record_id: str) -> bool:
        with self._lock:
            return record_id in self._cache

    def clear(self):
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0


# Global singleton instance of cache
ehr_cache = EHRRecordCache()


class RetrievalService:
    """Manages high-priority EHR retrieval, cache lookups, latency telemetry, and SLA adherence."""

    def __init__(self):
        self.cache = ehr_cache

    def retrieve_record(self, req: EmergencyRetrievalRequest) -> RetrievalJobResponse:
        """Executes retrieval request measuring exact latency against clinical SLA targets."""
        record = record_service.get_record(req.record_id)
        if not record:
            raise ValueError(f"Record with ID '{req.record_id}' not found.")

        req_time = datetime.now(timezone.utc)
        retrieval_id = f"RET_{uuid.uuid4().hex[:8].upper()}"

        tier_str = record.storage_tier.value if hasattr(record.storage_tier, "value") else str(record.storage_tier)
        s3_location = storage_service.get_s3_uri(record.record_id, record.record_type, StorageTier(tier_str) if tier_str in StorageTier.__members__ else StorageTier.STANDARD)

        # 1. Check in-memory Cache
        cached_data = self.cache.get(record.record_id)
        cache_hit = cached_data is not None

        # 2. Determine Latency
        if cache_hit:
            # Ultra-low latency from memory/edge cache (5 - 20 ms)
            latency_ms = round(random.uniform(5.0, 20.0), 2)
        else:
            # Latency dependent on AWS S3 Storage Tier
            if tier_str == StorageTier.STANDARD.value:
                # S3 Standard direct fetch: 55 - 120 ms
                latency_ms = round(random.uniform(55.0, 120.0), 2)
            elif tier_str == StorageTier.STANDARD_IA.value:
                # S3 Standard-IA fetch: 180 - 290 ms
                latency_ms = round(random.uniform(180.0, 290.0), 2)
            elif tier_str in [StorageTier.GLACIER_FLEXIBLE.value, "GLACIER"]:
                # S3 Glacier Flexible: Expedited restore (1-5 min) or Standard (3-5 hrs)
                # In simulation, we record standard restore delay in ms
                latency_ms = 180000.0  # 3 minutes in ms (violates 500ms emergency SLA)
            elif tier_str in [StorageTier.GLACIER_DEEP_ARCHIVE.value, "DEEP_ARCHIVE"]:
                # S3 Glacier Deep Archive: 12-48 hours
                latency_ms = 43200000.0  # 12 hours in ms
            else:
                latency_ms = round(random.uniform(60.0, 150.0), 2)

            # Warm cache with fetched record
            self.cache.put(record.record_id, record.model_dump())

        # 3. SLA Validation
        # Clinical Emergency SLA = 500 ms; Standard SLA = 5000 ms
        sla_target_ms = 500.0 if req.is_emergency else 5000.0
        sla_met = latency_ms <= sla_target_ms

        job_resp = RetrievalJobResponse(
            retrieval_id=retrieval_id,
            record_id=record.record_id,
            patient_id=record.patient_id,
            is_emergency=req.is_emergency,
            storage_tier=tier_str,
            cache_hit=cache_hit,
            retrieval_latency_ms=latency_ms,
            sla_target_ms=sla_target_ms,
            sla_met=sla_met,
            s3_location=s3_location,
            requested_at=req_time,
            completed_at=datetime.now(timezone.utc)
        )

        # 4. Persistence & Audit Logging
        db_memory.put_retrieval(job_resp.model_dump())

        # Record access log entry
        access_event = RawAccessEvent(
            event_id=f"EVT_{uuid.uuid4().hex[:6].upper()}",
            timestamp=req_time,
            patient_id=record.patient_id or f"P_SYN_{record.record_id}",
            record_type=record.record_type,
            department=req.department,
            access_type=AccessType.RETRIEVE,
            access_frequency=record.access_frequency + 1,
            data_size_mb=record.data_size_mb,
            criticality=Criticality(record.criticality) if record.criticality in Criticality.__members__ else Criticality.MEDIUM,
            storage_tier=StorageTier(tier_str) if tier_str in StorageTier.__members__ else StorageTier.STANDARD,
            emergency_flag=req.is_emergency,
            backup_status=None
        )
        record_service.record_access_event(access_event)

        logger.info(
            f"Retrieval {retrieval_id} for '{record.record_id}': Tier={tier_str}, "
            f"CacheHit={cache_hit}, Latency={latency_ms}ms, SLA Met={sla_met}"
        )
        return job_resp

    def prefetch_records(self, req: PrefetchRequest) -> PrefetchResponse:
        """Pre-warms cache with records identified by access demand forecast."""
        prefetched = []
        failed = []

        for rid in req.record_ids:
            rec = record_service.get_record(rid)
            if rec:
                self.cache.put(rec.record_id, rec.model_dump())
                prefetched.append(rec.record_id)
            else:
                failed.append(rid)

        logger.info(f"Prefetched {len(prefetched)} records into EHR cache (Failed: {len(failed)})")
        return PrefetchResponse(
            prefetched_count=len(prefetched),
            failed_count=len(failed),
            cached_record_ids=prefetched,
            prefetched_at=datetime.now(timezone.utc)
        )

    def get_metrics(self) -> RetrievalMetricsSummary:
        """Aggregates telemetry across all historical retrievals."""
        raw_jobs = db_memory.list_retrievals()
        total_count = len(raw_jobs)
        if total_count == 0:
            return RetrievalMetricsSummary()

        emergency_count = 0
        cache_hits = 0
        sla_violations = 0
        emergency_latencies: List[float] = []
        latencies_by_tier: Dict[str, List[float]] = {}

        for j in raw_jobs:
            lat = float(j.get("retrieval_latency_ms", 0.0))
            is_emer = bool(j.get("is_emergency", False))
            tier = str(j.get("storage_tier", "STANDARD"))
            hit = bool(j.get("cache_hit", False))
            sla_met = bool(j.get("sla_met", True))

            if is_emer:
                emergency_count += 1
                emergency_latencies.append(lat)

            if hit:
                cache_hits += 1

            if not sla_met:
                sla_violations += 1

            if tier not in latencies_by_tier:
                latencies_by_tier[tier] = []
            latencies_by_tier[tier].append(lat)

        avg_tier_lat = {t: round(sum(l) / len(l), 2) for t, l in latencies_by_tier.items()}
        avg_emer_lat = round(sum(emergency_latencies) / len(emergency_latencies), 2) if emergency_latencies else 0.0

        return RetrievalMetricsSummary(
            total_retrieval_requests=total_count,
            emergency_requests_count=emergency_count,
            cache_hits_count=cache_hits,
            cache_hit_rate_percent=round((cache_hits / total_count) * 100.0, 2),
            sla_violations_count=sla_violations,
            sla_violation_rate_percent=round((sla_violations / total_count) * 100.0, 2),
            average_latency_by_tier_ms=avg_tier_lat,
            average_emergency_latency_ms=avg_emer_lat
        )


retrieval_service = RetrievalService()
