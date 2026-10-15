from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional, Union
from pydantic import BaseModel
from app.models.record import RecordCreate, RecordResponse
from app.models.access_log import RawAccessEvent
from app.models.retrieval import EmergencyRetrievalRequest, RetrievalJobResponse
from app.services.record_service import record_service
from app.services.retrieval_service import retrieval_service

router = APIRouter()


class RecordRetrieveBody(BaseModel):
    is_emergency: bool = True
    department: str = "Emergency"
    reason: Optional[str] = "Clinical lookup"


@router.post("/records", response_model=RecordResponse, status_code=status.HTTP_201_CREATED, tags=["Records"])
def create_record(record_in: RecordCreate):
    """Register incoming hospital record, assign criticality, and store metadata."""
    existing = record_service.get_record(record_in.record_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Record with ID '{record_in.record_id}' already exists."
        )
    return record_service.create_record(record_in)


@router.get("/records", response_model=List[RecordResponse], tags=["Records"])
def list_records(
    criticality: Optional[str] = Query(None),
    storage_tier: Optional[str] = Query(None),
    emergency_only: bool = Query(False),
):
    """Retrieve list of registered hospital records."""
    return record_service.list_records(
        criticality=criticality,
        storage_tier=storage_tier,
        emergency_only=emergency_only,
    )


@router.post("/records/access-events", tags=["Records"])
def ingest_access_events(payload: Union[RawAccessEvent, List[RawAccessEvent]]):
    """Ingest a single access event or a batch of Synthea-derived access logs."""
    events = payload if isinstance(payload, list) else [payload]
    stored = [record_service.record_access_event(event) for event in events]
    return {"ingested": len(stored), "events": stored}


@router.get("/records/patient/{patient_id}/access-history", tags=["Records"])
def get_patient_access_history(patient_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Retrieve chronological access logs for a specific patient."""
    return record_service.list_access_events(patient_id=patient_id, limit=limit)


@router.post("/records/{record_id}/retrieve", response_model=RetrievalJobResponse, tags=["Records"])
def retrieve_record_by_id(record_id: str, body: Optional[RecordRetrieveBody] = None):
    """High-priority retrieval for a hospital record (contract alias of POST /retrieval/request)."""
    payload = body or RecordRetrieveBody()
    try:
        return retrieval_service.retrieve_record(
            EmergencyRetrievalRequest(
                record_id=record_id,
                is_emergency=payload.is_emergency,
                department=payload.department,
                reason=payload.reason,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/records/{record_id}/access-history", tags=["Records"])
def get_record_access_history(record_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Retrieve access logs linked to a specific record."""
    record = record_service.get_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
    events = record_service.list_access_events(record_id=record_id, limit=limit)
    if not events and record.patient_id:
        events = record_service.list_access_events(patient_id=record.patient_id, limit=limit)
    return events


@router.get("/records/{record_id}", response_model=RecordResponse, tags=["Records"])
def get_record(record_id: str):
    """Retrieve details of a specific hospital record."""
    record = record_service.get_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID '{record_id}' not found."
        )
    return record
