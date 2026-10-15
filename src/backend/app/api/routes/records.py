from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.record import RecordCreate, RecordResponse
from app.services.record_service import record_service

router = APIRouter()


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
def list_records():
    """Retrieve list of registered hospital records."""
    return record_service.list_records()


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
