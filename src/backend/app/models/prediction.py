from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List


# --- Preserved Backup-Volume Forecasting Models ---
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


# --- New Access-Demand Forecasting Models ---
class AccessDemandPredictionRequest(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Forecast reference timestamp")
    recent_access_counts: Optional[List[int]] = Field(default=None, description="24-hour sequence of hourly access event counts")
    current_access_count: int = Field(default=1200, ge=0, description="Current access event count in last hour")
    current_access_volume_mb: float = Field(default=15400.0, ge=0.0, description="Current access data volume in MB")
    emergency_context_ratio: float = Field(default=0.05, ge=0.0, le=1.0, description="Fraction of emergency accesses (0.0 to 1.0)")


class AccessDemandPredictionResponse(BaseModel):
    forecast_horizon: str = Field(default="1 hour", json_schema_extra={"example": "1 hour"})
    predicted_access_count: int = Field(..., description="Forecasted access event count for next hour")
    predicted_access_volume_mb: float = Field(..., description="Forecasted access volume in MB for next hour")
    predicted_emergency_count: int = Field(default=0, description="Forecasted emergency event count for next hour")
    confidence_interval_low: float = Field(..., description="Lower bound of predicted access volume")
    confidence_interval_high: float = Field(..., description="Upper bound of predicted access volume")
    model_version: str = Field(default="bilstm-access-v1", json_schema_extra={"example": "bilstm-access-v1"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Combined Joint Workload Forecast for Decision Engine ---
class JointWorkloadForecastResponse(BaseModel):
    forecast_horizon: str = Field(default="1 hour")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    backup_forecast: PredictionResponse
    access_forecast: AccessDemandPredictionResponse
    workload_intensity_level: str = Field(..., description="LOW, NORMAL, HIGH, or PEAK")
    recommendation: str = Field(..., description="Workload-based cloud orchestration directive")
