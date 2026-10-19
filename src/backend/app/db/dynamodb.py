from decimal import Decimal
import boto3
from typing import Dict, Any, List, Optional
from threading import Lock
from datetime import datetime, date, timezone
from enum import Enum
from app.core.config import settings
from app.core.logging import logger


def to_dynamodb_item(obj: Any) -> Any:
    """Converts floats to Decimals, datetimes to ISO strings, enums to values, and strips None."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_dynamodb_item(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [to_dynamodb_item(v) for v in obj]
    return obj


def from_dynamodb_item(obj: Any) -> Any:
    """Converts Decimals back to standard floats/ints from DynamoDB."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: from_dynamodb_item(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [from_dynamodb_item(v) for v in obj]
    return obj


class InMemoryDatabase:
    """Thread-safe database store with seamless live DynamoDB synchronization when active."""

    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._access_events: List[Dict[str, Any]] = []
        self._retrievals: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def _get_table(self, table_name: str):
        if settings.USE_MOCK_AWS or not settings.AWS_ACCESS_KEY_ID:
            return None
        try:
            ddb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
            return ddb.Table(table_name)
        except Exception as e:
            logger.warning(f"DynamoDB connection failed ({e}), using in-memory store.")
            return None

    # --- EHR Records ---
    def put_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._records[record["record_id"]] = record

        table = self._get_table(settings.DYNAMODB_TABLE_RECORDS)
        if table:
            try:
                table.put_item(Item=to_dynamodb_item(record))
            except Exception as e:
                logger.warning(f"DynamoDB PutItem failed for record {record.get('record_id')}: {e}")

        return record

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if record_id in self._records:
                return self._records[record_id]

        table = self._get_table(settings.DYNAMODB_TABLE_RECORDS)
        if table:
            try:
                resp = table.get_item(Key={"record_id": record_id})
                item = resp.get("Item")
                if item:
                    parsed = from_dynamodb_item(item)
                    with self._lock:
                        self._records[record_id] = parsed
                    return parsed
            except Exception as e:
                logger.warning(f"DynamoDB GetItem failed for {record_id}: {e}")

        return None

    def list_records(
        self,
        criticality: Optional[str] = None,
        storage_tier: Optional[str] = None,
        emergency_only: bool = False
    ) -> List[Dict[str, Any]]:
        table = self._get_table(settings.DYNAMODB_TABLE_RECORDS)
        if table:
            try:
                resp = table.scan()
                items = [from_dynamodb_item(it) for it in resp.get("Items", [])]
                with self._lock:
                    for it in items:
                        self._records[it["record_id"]] = it
            except Exception as e:
                logger.warning(f"DynamoDB scan failed ({e}), using local cache.")

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
            if rec:
                rec["storage_tier"] = new_tier
                rec["tier_updated_at"] = datetime.now(timezone.utc).isoformat()
                self._records[record_id] = rec

        table = self._get_table(settings.DYNAMODB_TABLE_RECORDS)
        if table:
            try:
                table.update_item(
                    Key={"record_id": record_id},
                    UpdateExpression="SET storage_tier = :t, tier_updated_at = :ts",
                    ExpressionAttributeValues={
                        ":t": new_tier,
                        ":ts": datetime.now(timezone.utc).isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"DynamoDB UpdateItem failed for {record_id}: {e}")

        return rec

    # --- Backup Jobs ---
    def put_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._jobs[job["job_id"]] = job

        table = self._get_table(settings.DYNAMODB_TABLE_JOBS)
        if table:
            try:
                table.put_item(Item=to_dynamodb_item(job))
            except Exception as e:
                logger.warning(f"DynamoDB PutItem failed for job {job.get('job_id')}: {e}")

        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id]

        table = self._get_table(settings.DYNAMODB_TABLE_JOBS)
        if table:
            try:
                resp = table.get_item(Key={"job_id": job_id})
                item = resp.get("Item")
                if item:
                    parsed = from_dynamodb_item(item)
                    with self._lock:
                        self._jobs[job_id] = parsed
                    return parsed
            except Exception as e:
                logger.warning(f"DynamoDB GetItem failed for job {job_id}: {e}")

        return None

    def list_jobs(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        table = self._get_table(settings.DYNAMODB_TABLE_JOBS)
        if table:
            try:
                resp = table.scan()
                items = [from_dynamodb_item(it) for it in resp.get("Items", [])]
                with self._lock:
                    for it in items:
                        self._jobs[it["job_id"]] = it
            except Exception as e:
                logger.warning(f"DynamoDB jobs scan failed ({e}), using memory.")

        with self._lock:
            jobs = list(self._jobs.values())
            if status_filter:
                return [j for j in jobs if j.get("status") == status_filter]
            return jobs

    # --- Access Event Logs ---
    def put_access_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._access_events.append(event)

        table = self._get_table(settings.DYNAMODB_TABLE_ACCESS_EVENTS)
        if table:
            try:
                table.put_item(Item=to_dynamodb_item(event))
            except Exception as e:
                logger.warning(f"DynamoDB access event put failed: {e}")

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

        table = self._get_table(settings.DYNAMODB_TABLE_RETRIEVALS)
        if table:
            try:
                table.put_item(Item=to_dynamodb_item(retrieval))
            except Exception as e:
                logger.warning(f"DynamoDB retrieval put failed: {e}")

        return retrieval

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


# Global singleton instance for database access
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

