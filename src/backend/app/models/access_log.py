from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from app.models.enums import AccessType, Criticality, StorageTier, BackupStatus


class RawAccessEvent(BaseModel):
    """Raw EHR access-event log schema matching Synthea-derived and simulated access logs."""
    event_id: str = Field(..., description="Unique event identifier (e.g. EVT_0001)")
    record_id: Optional[str] = Field(default=None, description="Linked EHR record identifier when known")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp (UTC)")
    patient_id: str = Field(..., description="Synthetic patient identifier (e.g. P_SYN_10482)")
    record_type: str = Field(..., description="Clinical record category (e.g. EHR, CT, MRI, Lab)")
    department: str = Field(..., description="Originating hospital department (e.g. Emergency, Cardiology, Radiology)")
    access_type: AccessType = Field(..., description="Explicit operation: READ, WRITE, UPDATE, RETRIEVE, BACKUP")
    access_frequency: int = Field(default=0, ge=0, description="Access count for patient/category in prior 24h")
    data_size_mb: float = Field(..., gt=0, description="Payload data size in MB")
    criticality: Criticality = Field(..., description="Clinical criticality: CRITICAL, HIGH, MEDIUM, LOW")
    storage_tier: StorageTier = Field(default=StorageTier.STANDARD, description="Current or assigned AWS storage tier")
    emergency_flag: bool = Field(default=False, description="Whether event occurred in an emergency context")
    backup_status: Optional[BackupStatus] = Field(default=None, description="Status for backup operations, None otherwise")

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "EVT_1001",
                "timestamp": "2026-10-11T14:30:00Z",
                "patient_id": "P_SYN_10482",
                "record_type": "EHR",
                "department": "Emergency",
                "access_type": "RETRIEVE",
                "access_frequency": 14,
                "data_size_mb": 12.5,
                "criticality": "CRITICAL",
                "storage_tier": "STANDARD",
                "emergency_flag": True,
                "backup_status": None
            }
        }
    }


class HourlyWorkloadWindow(BaseModel):
    """Hourly processed workload aggregation schema separating access and backup metrics."""
    window_start_time: datetime = Field(..., description="Start of the 1-hour time window (UTC)")
    access_event_count: int = Field(default=0, ge=0, description="Total count of access events in the hour")
    access_volume_mb: float = Field(default=0.0, ge=0.0, description="Total volume of accessed data in MB")
    backup_event_count: int = Field(default=0, ge=0, description="Total count of backup operations in the hour")
    backup_volume_mb: float = Field(default=0.0, ge=0.0, description="Total volume of backed-up data in MB")
    emergency_event_count: int = Field(default=0, ge=0, description="Total count of emergency events in the hour")
