from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.models.record import RecordCreate, RecordResponse
from app.db.dynamodb import db_memory
from app.core.logging import logger

CRITICALITY_MAP = {
    "Emergency EHR": "CRITICAL",
    "EHR": "CRITICAL",
    "ICU": "CRITICAL",
    "CT": "HIGH",
    "MRI": "HIGH",
    "Surgical": "HIGH",
    "Monitoring": "MEDIUM",
    "Outpatient": "MEDIUM",
    "Administrative": "LOW",
    "Billing": "LOW"
}

CRITICALITY_SCORE_MAP = {
    "CRITICAL": 4.0,
    "HIGH": 3.0,
    "MEDIUM": 2.0,
    "LOW": 1.0
}


def assign_criticality(record_type: str, department: str = "") -> str:
    """Assigns hospital record criticality based on record type and department."""
    dept_lower = department.lower()
    if "emergency" in dept_lower or "icu" in dept_lower:
        return "CRITICAL"

    return CRITICALITY_MAP.get(record_type, "MEDIUM")


def get_criticality_score(criticality: str) -> float:
    """Returns numerical weight for a criticality string."""
    return CRITICALITY_SCORE_MAP.get(criticality.upper(), 2.0)


class RecordService:
    def create_record(self, record_in: RecordCreate) -> RecordResponse:
        criticality = assign_criticality(record_in.record_type, record_in.department)

        record_dict = record_in.model_dump()
        record_dict.update({
            "criticality": criticality,
            "priority_score": 0.0,
            "backup_status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_backup": None
        })


        db_memory.put_record(record_dict)
        logger.info(f"Ingested record {record_in.record_id} with criticality {criticality}")

        return RecordResponse(**record_dict)

    def get_record(self, record_id: str) -> Optional[RecordResponse]:
        record_data = db_memory.get_record(record_id)
        if not record_data:
            return None
        return RecordResponse(**record_data)

    def list_records(self) -> List[RecordResponse]:
        records_data = db_memory.list_records()
        return [RecordResponse(**r) for r in records_data]


record_service = RecordService()
