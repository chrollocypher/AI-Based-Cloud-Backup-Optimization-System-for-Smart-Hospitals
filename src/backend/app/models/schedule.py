from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional


class ScheduleItem(BaseModel):
    record_id: str = Field(..., json_schema_extra={"example": "EHR_10025"})
    record_type: str = Field(..., json_schema_extra={"example": "EHR"})
    department: str = Field(..., json_schema_extra={"example": "Emergency"})
    criticality: str = Field(..., json_schema_extra={"example": "CRITICAL"})
    priority_score: float = Field(..., json_schema_extra={"example": 3.85})
    data_size_mb: float = Field(..., json_schema_extra={"example": 25.4})
    action: str = Field(..., json_schema_extra={"example": "BACKUP_NOW"}, description="Action: BACKUP_NOW, BACKUP_NEXT, DEFER")
    reason: Optional[str] = None


class ScheduleResponse(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    predicted_workload_mb: float = Field(..., json_schema_extra={"example": 11600.0})
    capacity_threshold_mb: float = Field(..., json_schema_extra={"example": 10000.0})
    is_capacity_exceeded: bool = Field(..., json_schema_extra={"example": True})
    total_pending_records: int = Field(..., json_schema_extra={"example": 6})
    scheduled_now_count: int = Field(..., json_schema_extra={"example": 4})
    deferred_count: int = Field(..., json_schema_extra={"example": 2})
    schedule: List[ScheduleItem]
