from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional


class RecordCreate(BaseModel):
    record_id: str = Field(..., json_schema_extra={"example": "EHR_10025"}, description="Unique hospital record identifier")
    record_type: str = Field(..., json_schema_extra={"example": "EHR"}, description="Type of hospital record (e.g. EHR, CT, MRI, Monitoring)")
    department: str = Field(..., json_schema_extra={"example": "Emergency"}, description="Originating hospital department")
    data_size_mb: float = Field(..., gt=0, json_schema_extra={"example": 25.4}, description="Size of the record in MB")
    access_frequency: int = Field(..., ge=0, json_schema_extra={"example": 18}, description="Access frequency count in last 24h")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Record generation timestamp")


    model_config = {
        "json_schema_extra": {
            "example": {
                "record_id": "EHR_10025",
                "record_type": "EHR",
                "department": "Emergency",
                "data_size_mb": 25.4,
                "access_frequency": 18,
                "timestamp": "2026-09-19T10:15:00Z"
            }
        }
    }


class RecordResponse(RecordCreate):
    criticality: str = Field(..., json_schema_extra={"example": "CRITICAL"}, description="Assigned criticality level: CRITICAL, HIGH, MEDIUM, LOW")
    priority_score: float = Field(default=0.0, json_schema_extra={"example": 3.85}, description="Calculated urgency priority score")
    backup_status: str = Field(default="PENDING", json_schema_extra={"example": "PENDING"}, description="Backup status: PENDING, SCHEDULED, IN_PROGRESS, COMPLETED, FAILED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_backup: Optional[datetime] = None

