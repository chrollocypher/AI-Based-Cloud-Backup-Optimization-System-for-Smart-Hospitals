from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional


class PredictionRequest(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Forecast reference timestamp")
    data_volume_mb: float = Field(..., gt=0, json_schema_extra={"example": 8200.0}, description="Current observed hospital data volume in MB")
    access_frequency: int = Field(..., ge=0, json_schema_extra={"example": 530}, description="Current aggregate access frequency")
    active_departments: Optional[int] = Field(default=8, json_schema_extra={"example": 8}, description="Number of active hospital departments")


class PredictionResponse(BaseModel):
    forecast_horizon: str = Field(default="1 hour", json_schema_extra={"example": "1 hour"})
    predicted_backup_volume_mb: float = Field(..., json_schema_extra={"example": 11600.0}, description="Predicted workload volume in MB for next horizon")
    confidence_interval_low: float = Field(..., json_schema_extra={"example": 10500.0})
    confidence_interval_high: float = Field(..., json_schema_extra={"example": 12700.0})
    model_version: str = Field(default="lstm-v1", json_schema_extra={"example": "lstm-v1"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
