import boto3
from typing import Dict, Any, List, Optional
from threading import Lock
from datetime import datetime, timezone
from app.core.config import settings
from app.core.logging import logger


class InMemoryDatabase:
    """Thread-safe in-memory database store for development, simulation, and testing."""

    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._access_events: List[Dict[str, Any]] = []
        self._retrievals: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    # --- EHR Records ---
    def put_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._records[record["record_id"]] = record
            return record

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._records.get(record_id)

    def list_records(
        self,
        criticality: Optional[str] = None,
        storage_tier: Optional[str] = None,
        emergency_only: bool = False
    ) -> List[Dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
            if criticality:
                records = [r for r in records if r.get("criticality") == criticality]
            if storage_tier:
                records = [r for r in records if r.get("storage_tier") == storage_tier]
            if emergency_only:
                records = [r for r in records if r.get("emergency_flag") is True]
            return records

    def update_record_tier(self, record_id: str, new_tier: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._records.get(record_id)
            if not rec:
                return None
            rec["storage_tier"] = new_tier
            rec["tier_updated_at"] = datetime.now(timezone.utc).isoformat()
            self._records[record_id] = rec
            return rec

    # --- Backup Jobs ---
    def put_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._jobs[job["job_id"]] = job
            return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
            if status_filter:
                return [j for j in jobs if j.get("status") == status_filter]
            return jobs

    # --- Access Event Logs ---
    def put_access_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._access_events.append(event)
            return event

    def list_access_events(
        self,
        patient_id: Optional[str] = None,
        record_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._lock:
            events = self._access_events
            if patient_id:
                events = [e for e in events if e.get("patient_id") == patient_id]
            if record_id:
                events = [e for e in events if e.get("record_id") == record_id]
            return events[-limit:]

    # --- Retrieval & Emergency Jobs ---
    def put_retrieval(self, retrieval: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._retrievals[retrieval["retrieval_id"]] = retrieval
            return retrieval

    def get_retrieval(self, retrieval_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._retrievals.get(retrieval_id)

    def list_retrievals(self, is_emergency: Optional[bool] = None) -> List[Dict[str, Any]]:
        with self._lock:
            rets = list(self._retrievals.values())
            if is_emergency is not None:
                rets = [r for r in rets if r.get("is_emergency") == is_emergency]
            return rets

    def clear(self):
        with self._lock:
            self._records.clear()
            self._jobs.clear()
            self._access_events.clear()
            self._retrievals.clear()


# Global singleton instance for local in-memory fallback
db_memory = InMemoryDatabase()


def get_dynamodb_resource():
    """Returns DynamoDB boto3 resource or None if mock mode is active."""
    if settings.USE_MOCK_AWS or not settings.AWS_ACCESS_KEY_ID:
        return None
    try:
        return boto3.resource(
            "dynamodb",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    except Exception as e:
        logger.warning(f"Could not connect to DynamoDB: {e}. Falling back to in-memory store.")
        return None
