"""AWS Lambda task for querying joint workload forecast (backup volume + access demand)."""
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    from app.services.prediction_service import prediction_service

    joint = prediction_service.get_joint_workload_forecast()
    return joint.model_dump()
