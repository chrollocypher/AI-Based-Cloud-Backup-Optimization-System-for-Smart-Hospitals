import json
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.core.logging import logger
from app.models.enums import StorageTier, TierLabel, Criticality, map_tier_label_to_aws_class
from app.models.storage import (
    StorageTierTransitionRequest,
    StorageTierTransitionResponse,
    CostBreakdownItem,
    StorageCostEvaluationResponse
)
from app.services.record_service import record_service


# AWS us-east-1 Standard S3 Pricing Model (per GB and per request)
TIER_PRICING = {
    StorageTier.STANDARD.value: {
        "storage_per_gb_month": 0.023,
        "put_copy_per_1000": 0.005,
        "get_per_1000": 0.0004,
        "retrieval_per_gb": 0.0,
        "min_duration_days": 0,
        "restore_delay_desc": "Immediate (<100 ms)"
    },
    StorageTier.STANDARD_IA.value: {
        "storage_per_gb_month": 0.0125,
        "put_copy_per_1000": 0.01,
        "get_per_1000": 0.001,
        "retrieval_per_gb": 0.01,
        "min_duration_days": 30,
        "restore_delay_desc": "Immediate (<250 ms)"
    },
    StorageTier.GLACIER_FLEXIBLE.value: {
        "storage_per_gb_month": 0.0036,
        "put_copy_per_1000": 0.05,
        "get_per_1000": 0.0004,
        "retrieval_per_gb": 0.01,  # Standard tier retrieval
        "min_duration_days": 90,
        "restore_delay_desc": "Expedited 1-5 min / Standard 3-5 hours"
    },
    StorageTier.GLACIER_DEEP_ARCHIVE.value: {
        "storage_per_gb_month": 0.00099,
        "put_copy_per_1000": 0.05,
        "get_per_1000": 0.0004,
        "retrieval_per_gb": 0.02,
        "min_duration_days": 180,
        "restore_delay_desc": "Standard 12 hours / Bulk 48 hours"
    }
}


class StorageService:
    """Manages AWS S3 multi-tier storage classes, transition rules,

    clinical safety guardrails, and cloud cost accounting.
    """

    def __init__(self):
        self.bucket_name = "smart-hospital-ehr"

    def get_s3_uri(self, record_id: str, record_type: str, tier: StorageTier) -> str:
        """Constructs canonical S3 URI for a tiered EHR record."""
        tier_folder = tier.value.lower()
        return f"s3://{self.bucket_name}/{tier_folder}/{record_type.lower()}/{record_id}.json"

    def transition_tier(self, req: StorageTierTransitionRequest) -> StorageTierTransitionResponse:
        """Executes storage tier transition enforcing clinical safety guardrails."""
        record = record_service.get_record(req.record_id)
        if not record:
            raise ValueError(f"Record '{req.record_id}' not found.")

        target_aws_class = map_tier_label_to_aws_class(req.target_tier)
        previous_tier = record.storage_tier.value if hasattr(record.storage_tier, "value") else str(record.storage_tier)

        safety_rule_applied = False
        final_target_tier = target_aws_class

        # CLINICAL SAFETY GUARDRAIL:
        # A record with CRITICAL status or emergency_flag=True CANNOT be placed in cold archive
        is_critical_or_emergency = (
            record.criticality == Criticality.CRITICAL.value or
            record.criticality == "CRITICAL" or
            record.emergency_flag is True
        )

        if is_critical_or_emergency and target_aws_class in [StorageTier.GLACIER_FLEXIBLE, StorageTier.GLACIER_DEEP_ARCHIVE]:
            if not req.force_override:
                # Intercept unsafe transition and clamp to STANDARD_IA (WARM) to satisfy emergency retrieval SLAs
                final_target_tier = StorageTier.STANDARD_IA
                safety_rule_applied = True
                logger.warning(
                    f"[SAFETY RULE] Blocked archiving CRITICAL record '{req.record_id}' to Glacier. "
                    f"Clamped target to {StorageTier.STANDARD_IA.value}."
                )

        # Execute S3 transition (Live Boto3 or Mock)
        s3_uri = self.get_s3_uri(record.record_id, record.record_type, final_target_tier)
        if not settings.USE_MOCK_AWS and settings.AWS_ACCESS_KEY_ID:
            try:
                s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
                source_key = f"{previous_tier.lower()}/{record.record_type.lower()}/{record.record_id}.json"
                dest_key = f"{final_target_tier.value.lower()}/{record.record_type.lower()}/{record.record_id}.json"

                s3_client.copy_object(
                    Bucket=self.bucket_name,
                    CopySource={"Bucket": self.bucket_name, "Key": source_key},
                    Key=dest_key,
                    StorageClass=final_target_tier.value,
                    MetadataDirective="COPY"
                )
                logger.info(f"Boto3 copied S3 object {source_key} -> {dest_key} ({final_target_tier.value})")
            except Exception as e:
                logger.warning(f"Boto3 copy failed ({e}), recording simulated transition.")

        # Update database record
        record_service.update_tier(record.record_id, final_target_tier.value)

        return StorageTierTransitionResponse(
            record_id=record.record_id,
            previous_tier=previous_tier,
            new_tier=final_target_tier.value,
            aws_storage_class=final_target_tier,
            s3_location=s3_uri,
            status="SUCCESS",
            safety_rule_applied=safety_rule_applied,
            transitioned_at=datetime.now(timezone.utc)
        )

    def evaluate_storage_costs(self, pricing_region: str = "us-east-1") -> StorageCostEvaluationResponse:
        """Evaluates monthly storage & retrieval costs comparing proposed tiering policy

        against a static S3 Standard baseline policy.
        """
        records = record_service.list_records()
        if not records:
            # Generate empty report if no records present
            return StorageCostEvaluationResponse(
                pricing_region=pricing_region,
                total_records=0,
                total_volume_gb=0.0,
                proposed_policy_monthly_cost_usd=0.0,
                static_standard_monthly_cost_usd=0.0,
                projected_monthly_savings_usd=0.0,
                savings_percentage=0.0,
                breakdown_by_tier=[],
                clinical_safety_protected_count=0
            )

        # Aggregate data by tier
        tier_data: Dict[str, Dict[str, Any]] = {
            StorageTier.STANDARD.value: {"count": 0, "volume_mb": 0.0, "accesses": 0},
            StorageTier.STANDARD_IA.value: {"count": 0, "volume_mb": 0.0, "accesses": 0},
            StorageTier.GLACIER_FLEXIBLE.value: {"count": 0, "volume_mb": 0.0, "accesses": 0},
            StorageTier.GLACIER_DEEP_ARCHIVE.value: {"count": 0, "volume_mb": 0.0, "accesses": 0},
        }

        total_volume_mb = 0.0
        safety_protected_count = 0

        for r in records:
            tier_key = r.storage_tier.value if hasattr(r.storage_tier, "value") else str(r.storage_tier)
            if tier_key not in tier_data:
                tier_key = StorageTier.STANDARD.value

            tier_data[tier_key]["count"] += 1
            tier_data[tier_key]["volume_mb"] += r.data_size_mb
            tier_data[tier_key]["accesses"] += r.access_frequency
            total_volume_mb += r.data_size_mb

            if r.criticality in ["CRITICAL", Criticality.CRITICAL.value] or r.emergency_flag:
                safety_protected_count += 1

        total_volume_gb = total_volume_mb / 1024.0

        # Calculate costs for proposed multi-tier policy
        proposed_total_cost = 0.0
        breakdown_items: List[CostBreakdownItem] = []

        for tier_name, data in tier_data.items():
            pricing = TIER_PRICING.get(tier_name, TIER_PRICING[StorageTier.STANDARD.value])
            volume_gb = data["volume_mb"] / 1024.0

            storage_cost = volume_gb * pricing["storage_per_gb_month"]
            # Estimate monthly requests (PUT once, plus monthly GET access events)
            request_cost = ((data["count"] / 1000.0) * pricing["put_copy_per_1000"]) + \
                           ((data["accesses"] / 1000.0) * pricing["get_per_1000"])
            # Retrieval fee (for IA and Glacier when accessed)
            retrieval_cost = (volume_gb * 0.1) * pricing["retrieval_per_gb"]

            tier_total = storage_cost + request_cost + retrieval_cost
            proposed_total_cost += tier_total

            breakdown_items.append(CostBreakdownItem(
                tier=tier_name,
                record_count=data["count"],
                total_volume_gb=round(volume_gb, 4),
                monthly_storage_cost_usd=round(storage_cost, 4),
                monthly_request_cost_usd=round(request_cost, 4),
                monthly_retrieval_cost_usd=round(retrieval_cost, 4),
                total_monthly_cost_usd=round(tier_total, 4)
            ))

        # Calculate baseline cost: All records stored in S3 Standard
        std_pricing = TIER_PRICING[StorageTier.STANDARD.value]
        total_accesses = sum(d["accesses"] for d in tier_data.values())
        static_storage_cost = total_volume_gb * std_pricing["storage_per_gb_month"]
        static_request_cost = ((len(records) / 1000.0) * std_pricing["put_copy_per_1000"]) + \
                              ((total_accesses / 1000.0) * std_pricing["get_per_1000"])
        static_total_cost = static_storage_cost + static_request_cost

        savings_usd = max(0.0, static_total_cost - proposed_total_cost)
        savings_pct = (savings_usd / max(static_total_cost, 0.0001)) * 100.0

        return StorageCostEvaluationResponse(
            pricing_region=pricing_region,
            total_records=len(records),
            total_volume_gb=round(total_volume_gb, 4),
            proposed_policy_monthly_cost_usd=round(proposed_total_cost, 4),
            static_standard_monthly_cost_usd=round(static_total_cost, 4),
            projected_monthly_savings_usd=round(savings_usd, 4),
            savings_percentage=round(savings_pct, 2),
            breakdown_by_tier=breakdown_items,
            clinical_safety_protected_count=safety_protected_count,
            calculated_at=datetime.now(timezone.utc)
        )


storage_service = StorageService()
