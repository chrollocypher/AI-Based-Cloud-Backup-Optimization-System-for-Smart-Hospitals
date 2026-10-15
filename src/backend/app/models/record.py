from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from app.models.enums import StorageTier, Criticality, BackupStatus


class RecordCreate(BaseModel):
    record_id: str = Field(..., json_schema_extra={"example": "EHR_10025"}, description="Unique hospital record identifier")
    patient_id: Optional[str] = Field(default=None, json_schema_extra={"example": "P_SYN_10482"}, description="Synthetic patient identifier")
    record_type: str = Field(..., json_schema_extra={"example": "EHR"}, description="Type of hospital record (e.g. EHR, CT, MRI, Monitoring)")
    department: str = Field(..., json_schema_extra={"example": "Emergency"}, description="Originating hospital department")
    data_size_mb: float = Field(..., gt=0, json_schema_extra={"example": 25.4}, description="Size of the record in MB")
    access_frequency: int = Field(..., ge=0, json_schema_extra={"example": 18}, description="Access frequency count in last 24h")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Record generation timestamp")
    storage_tier: StorageTier = Field(default=StorageTier.STANDARD, description="Assigned AWS S3 storage tier")
    emergency_flag: bool = Field(default=False, description="Emergency context flag")

    model_config = {
        "json_schema_extra": {
            "example": {
                "record_id": "EHR_10025",
                "patient_id": "P_SYN_10482",
                "record_type": "EHR",
                "department": "Emergency",
                "data_size_mb": 25.4,
                "access_frequency": 18,
                "timestamp": "2026-09-19T10:15:00Z",
                "storage_tier": "STANDARD",
                "emergency_flag": False
            }
        }
    }


class RecordResponse(RecordCreate):
    criticality: str = Field(..., json_schema_extra={"example": "CRITICAL"}, description="Assigned criticality level: CRITICAL, HIGH, MEDIUM, LOW")
    priority_score: float = Field(default=0.0, json_schema_extra={"example": 3.85}, description="Calculated urgency priority score")
    backup_status: str = Field(default="PENDING", json_schema_extra={"example": "PENDING"}, description="Backup status: PENDING, SCHEDULED, IN_PROGRESS, COMPLETED, FAILED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_backup: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    s3_location: Optional[str] = None
