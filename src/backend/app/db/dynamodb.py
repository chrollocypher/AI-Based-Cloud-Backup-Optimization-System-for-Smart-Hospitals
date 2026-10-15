import boto3
from typing import Dict, Any, List, Optional
from threading import Lock
from app.core.config import settings
from app.core.logging import logger


class InMemoryDatabase:
    """Thread-safe in-memory database store for development and testing."""

    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def put_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._records[record["record_id"]] = record
            return record

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._records.get(record_id)

    def list_records(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._records.values())

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

    def clear(self):
        with self._lock:
            self._records.clear()
            self._jobs.clear()


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
