from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List, Dict
from app.models.enums import StorageTier


class StorageTierTransitionRequest(BaseModel):
    record_id: str = Field(..., description="Unique record identifier")
    target_tier: str = Field(..., description="Target tier label (HOT, WARM, COLD, ARCHIVE) or S3 class (STANDARD, STANDARD_IA, GLACIER)")
    reason: Optional[str] = Field(default="ML access-demand optimization", description="Reason for tier transition")
    force_override: bool = Field(default=False, description="Whether to bypass non-safety warnings")


class StorageTierTransitionResponse(BaseModel):
    record_id: str = Field(..., description="Unique record identifier")
    previous_tier: str = Field(...)
    new_tier: str = Field(...)
    aws_storage_class: StorageTier = Field(...)
    s3_location: str = Field(...)
    status: str = Field(default="SUCCESS")
    safety_rule_applied: bool = Field(default=False)
    transitioned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CostBreakdownItem(BaseModel):
    tier: str
    record_count: int
    total_volume_gb: float
    monthly_storage_cost_usd: float
    monthly_request_cost_usd: float
    monthly_retrieval_cost_usd: float
    total_monthly_cost_usd: float


class StorageCostEvaluationResponse(BaseModel):
    pricing_region: str = Field(default="us-east-1")
    total_records: int
    total_volume_gb: float
    proposed_policy_monthly_cost_usd: float
    static_standard_monthly_cost_usd: float
    projected_monthly_savings_usd: float
    savings_percentage: float
    breakdown_by_tier: List[CostBreakdownItem]
    clinical_safety_protected_count: int
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
