"""AWS Lambda task for summarizing pipeline execution and publishing telemetry."""
from datetime import datetime, timezone
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    transitions = event.get("transitions_result", {})
    forecast = event.get("forecast", {})

    summary = {
        "pipeline_completed_at": datetime.now(timezone.utc).isoformat(),
        "workload_intensity_level": forecast.get("workload_intensity_level", "NORMAL"),
        "transitions_executed": transitions.get("transitions_executed_count", 0),
        "transitions_failed": transitions.get("transitions_failed_count", 0),
        "status": "COMPLETED"
    }
    return summary
