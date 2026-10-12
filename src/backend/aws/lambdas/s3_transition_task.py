"""AWS Lambda task for executing batch S3 transitions and updating DynamoDB metadata."""
from typing import Dict, Any, List


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    from app.services.storage_service import storage_service
    from app.models.storage import StorageTierTransitionRequest

    decisions_info = event.get("decisions", {})
    decisions = decisions_info.get("decisions", [])

    executed: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for d in decisions:
        if d.get("needs_transition"):
            try:
                res = storage_service.transition_tier(StorageTierTransitionRequest(
                    record_id=d["record_id"],
                    target_tier=d["target_tier"],
                    reason=d.get("reason", "Step Function pipeline execution")
                ))
                executed.append(res.model_dump())
            except Exception as e:
                executed.append({"record_id": d["record_id"], "error": str(e), "status": "FAILED"})
        else:
            skipped.append(d["record_id"])

    return {
        "transitions_executed_count": len([e for e in executed if e.get("status") != "FAILED"]),
        "transitions_failed_count": len([e for e in executed if e.get("status") == "FAILED"]),
        "unchanged_count": len(skipped),
        "executed_details": executed
    }
