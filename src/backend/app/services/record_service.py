from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.models.record import RecordCreate, RecordResponse
from app.models.access_log import RawAccessEvent
from app.models.enums import StorageTier, Criticality, CRITICALITY_WEIGHTS, map_tier_label_to_aws_class
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
    if "emergency" in dept_lower or "icu" in dept_lower or "trauma" in dept_lower:
        return "CRITICAL"
    return CRITICALITY_MAP.get(record_type, "MEDIUM")


def get_criticality_score(criticality: str) -> float:
    """Returns numerical weight for a criticality string."""
    return CRITICALITY_SCORE_MAP.get(criticality.upper(), 2.0)


class RecordService:
    def create_record(self, record_in: RecordCreate) -> RecordResponse:
        criticality = assign_criticality(record_in.record_type, record_in.department)
        crit_score = get_criticality_score(criticality)

        # Priority calculation incorporating criticality and access frequency
        priority_score = round(crit_score + min(record_in.access_frequency / 10.0, 1.0), 2)

        # Emergency flag derived if department is Emergency/ICU or explicitly set
        is_emergency = record_in.emergency_flag or (criticality == "CRITICAL" and "emergency" in record_in.department.lower())

        patient_id = record_in.patient_id or f"P_SYN_{record_in.record_id}"
        tier = record_in.storage_tier.value if hasattr(record_in.storage_tier, "value") else str(record_in.storage_tier)

        record_dict = record_in.model_dump()
        record_dict.update({
            "patient_id": patient_id,
            "criticality": criticality,
            "priority_score": priority_score,
            "storage_tier": tier,
            "emergency_flag": is_emergency,
            "backup_status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_backup": None,
            "last_accessed_at": datetime.now(timezone.utc).isoformat()
        })

        db_memory.put_record(record_dict)
        logger.info(f"Ingested record {record_in.record_id} (Patient: {patient_id}) with tier {tier}, criticality {criticality}")

        return RecordResponse(**record_dict)

    def get_record(self, record_id: str) -> Optional[RecordResponse]:
        record_data = db_memory.get_record(record_id)
        if not record_data:
            return None
        return RecordResponse(**record_data)

    def list_records(
        self,
        criticality: Optional[str] = None,
        storage_tier: Optional[str] = None,
        emergency_only: bool = False
    ) -> List[RecordResponse]:
        records_data = db_memory.list_records(
            criticality=criticality,
            storage_tier=storage_tier,
            emergency_only=emergency_only
        )
        return [RecordResponse(**r) for r in records_data]

    def update_tier(self, record_id: str, new_tier: str) -> Optional[RecordResponse]:
        """Update storage tier for a record adhering to AWS S3 storage classes."""
        aws_tier = map_tier_label_to_aws_class(new_tier).value
        updated = db_memory.update_record_tier(record_id, aws_tier)
        if not updated:
            return None
        logger.info(f"Updated record {record_id} tier to {aws_tier}")
        return RecordResponse(**updated)

    def record_access_event(self, event_in: RawAccessEvent) -> Dict[str, Any]:
        """Log an EHR access event and update record last_accessed_at and access_frequency."""
        event_dict = event_in.model_dump()
        event_dict["timestamp"] = event_in.timestamp.isoformat()
        if hasattr(event_in.storage_tier, "value"):
            event_dict["storage_tier"] = event_in.storage_tier.value
        if hasattr(event_in.access_type, "value"):
            event_dict["access_type"] = event_in.access_type.value
        if hasattr(event_in.criticality, "value"):
            event_dict["criticality"] = event_in.criticality.value

        rec = None
        if event_in.record_id:
            rec = db_memory.get_record(event_in.record_id)
        if rec is None:
            rec = db_memory.get_record(event_in.event_id)
        if rec is None:
            for candidate in db_memory.list_records():
                if candidate.get("patient_id") == event_in.patient_id:
                    rec = candidate
                    break

        if rec:
            event_dict["record_id"] = rec["record_id"]
            rec["last_accessed_at"] = event_dict["timestamp"]
            rec["access_frequency"] = rec.get("access_frequency", 0) + 1
            db_memory.put_record(rec)

        db_memory.put_access_event(event_dict)
        return event_dict

    def list_access_events(
        self,
        patient_id: Optional[str] = None,
        record_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return db_memory.list_access_events(patient_id=patient_id, record_id=record_id, limit=limit)


record_service = RecordService()
