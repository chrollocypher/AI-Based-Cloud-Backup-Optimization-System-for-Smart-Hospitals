from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List


class BackupJobCreate(BaseModel):
    record_id: Optional[str] = Field(default=None, json_schema_extra={"example": "EHR_10025"}, description="Specific record ID to backup, or empty to execute active schedule")


class BackupJobResponse(BaseModel):
    job_id: str = Field(..., json_schema_extra={"example": "JOB_1001"})
    record_id: str = Field(..., json_schema_extra={"example": "EHR_10025"})
    scheduled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(default="IN_PROGRESS", json_schema_extra={"example": "COMPLETED"}, description="Job status: PENDING, IN_PROGRESS, COMPLETED, FAILED")
    s3_location: Optional[str] = Field(default=None, json_schema_extra={"example": "s3://smart-hospital-backups/ehr/EHR_10025.bak"})
    error_message: Optional[str] = None
    execution_arn: Optional[str] = None
