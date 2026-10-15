"""AWS Lambda task for evaluating record storage tier decisions based on predicted demand,

clinical criticality, and safety guardrails.
"""
from typing import Dict, Any, List


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    from app.services.record_service import record_service
    from app.models.enums import StorageTier, Criticality

    forecast = event.get("forecast", {})
    workload_level = forecast.get("workload_intensity_level", "NORMAL")
    records = record_service.list_records()

    decisions: List[Dict[str, Any]] = []

    for r in records:
        rec_id = r.record_id
        is_crit = r.criticality in ["CRITICAL", Criticality.CRITICAL.value] or r.emergency_flag
        access_freq = r.access_frequency

        # Decision Policy:
        # 1. Critical or active emergency -> Must remain HOT (STANDARD)
        if is_crit:
            target_tier = StorageTier.STANDARD.value
            reason = "Clinical safety guardrail: Emergency/critical record kept in hot tier"
        elif access_freq >= 10:
            target_tier = StorageTier.STANDARD.value
            reason = "High 24h access frequency"
        elif access_freq == 0:
            target_tier = StorageTier.GLACIER_FLEXIBLE.value
            reason = "Cold archival: Zero recent access and non-critical status"
        else:
            target_tier = StorageTier.STANDARD_IA.value
            reason = "Moderate access demand"

        current_tier = r.storage_tier.value if hasattr(r.storage_tier, "value") else str(r.storage_tier)
        needs_transition = (current_tier != target_tier)

        decisions.append({
            "record_id": rec_id,
            "current_tier": current_tier,
            "target_tier": target_tier,
            "needs_transition": needs_transition,
            "reason": reason
        })

    return {
        "total_evaluated": len(records),
        "transitions_recommended": sum(1 for d in decisions if d["needs_transition"]),
        "decisions": decisions
    }
