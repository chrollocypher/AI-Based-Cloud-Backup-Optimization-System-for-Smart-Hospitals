from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from app.models.enums import StorageTier


class EmergencyRetrievalRequest(BaseModel):
    """Payload for initiating a hospital record retrieval."""
    record_id: str = Field(..., description="Target record identifier (e.g. REC_10025)")
    is_emergency: bool = Field(default=False, description="Flag indicating emergency retrieval requirement")
    department: str = Field(default="Emergency", description="Requesting department (e.g. Emergency, ICU, General)")
    reason: Optional[str] = Field(default="Emergency clinical care", description="Clinical reason for retrieval")


class RetrievalJobResponse(BaseModel):
    """Record retrieval execution outcome including latency and SLA adherence."""
    retrieval_id: str = Field(..., description="Unique retrieval tracking ID")
    record_id: str = Field(..., description="Retrieved record identifier")
    patient_id: Optional[str] = Field(default=None, description="Patient identifier")
    is_emergency: bool = Field(..., description="Whether this was an emergency request")
    storage_tier: StorageTier = Field(..., description="Storage class where record was located at retrieval time")
    cache_hit: bool = Field(default=False, description="Whether record was served from low-latency cache")
    retrieval_latency_ms: float = Field(..., ge=0.0, description="Measured request-to-available latency in milliseconds")
    sla_target_ms: float = Field(default=500.0, description="SLA threshold in ms (e.g. 500ms for emergency)")
    sla_met: bool = Field(..., description="True if retrieval_latency_ms <= sla_target_ms")
    s3_location: Optional[str] = Field(default=None, description="Source S3 URI of the record object")
    requested_at: datetime = Field(..., description="Timestamp when retrieval was requested")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Completion timestamp")


class RetrievalMetricsSummary(BaseModel):
    """Aggregate telemetry for emergency retrieval and storage performance."""
    total_retrieval_requests: int = Field(default=0)
    emergency_requests_count: int = Field(default=0)
    cache_hits_count: int = Field(default=0)
    cache_hit_rate_percent: float = Field(default=0.0)
    sla_violations_count: int = Field(default=0)
    sla_violation_rate_percent: float = Field(default=0.0)
    average_latency_by_tier_ms: dict[str, float] = Field(default_factory=dict)
    average_emergency_latency_ms: float = Field(default=0.0)
