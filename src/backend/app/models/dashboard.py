from pydantic import BaseModel, Field
from typing import List, Optional


class DashboardSummaryResponse(BaseModel):
    current_workload_gb: float = Field(..., json_schema_extra={"example": 8.2}, description="Current aggregate hospital workload in GB")
    predicted_workload_gb: float = Field(..., json_schema_extra={"example": 11.6}, description="Forecasted workload volume in GB")
    pending_backups: int = Field(..., json_schema_extra={"example": 24}, description="Count of pending backup records")
    critical_pending: int = Field(..., json_schema_extra={"example": 5}, description="Count of critical pending backup records")
    completed_today: int = Field(..., json_schema_extra={"example": 148}, description="Backups completed today")
    failed_today: int = Field(..., json_schema_extra={"example": 3}, description="Failed backup jobs count")
    storage_used_gb: float = Field(..., json_schema_extra={"example": 1420.5}, description="Total cloud storage consumed in S3")


class WorkloadPoint(BaseModel):
    timestamp: str = Field(..., json_schema_extra={"example": "10:00"})
    actual_gb: float = Field(..., json_schema_extra={"example": 8.2})
    predicted_gb: float = Field(..., json_schema_extra={"example": 8.9})


class MonitoringStatusResponse(BaseModel):
    system_status: str = Field(default="HEALTHY", json_schema_extra={"example": "HEALTHY"})
    database_connected: bool = Field(default=True)
    aws_services_active: bool = Field(default=True)
    active_scheduler: bool = Field(default=True)
    last_prediction_time: str = Field(..., json_schema_extra={"example": "2026-09-19T22:00:00Z"})
    active_jobs_count: int = Field(default=0)
