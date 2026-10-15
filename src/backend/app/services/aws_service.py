import json
import uuid
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger


class AWSService:
    """Service layer isolating AWS Boto3 API interactions for Step Functions, S3, and DynamoDB."""

    def trigger_step_function(self, record_id: str, priority_score: float, execution_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Triggers Step Functions state machine execution for backup processing."""
        exec_id = f"exec-{record_id}-{uuid.uuid4().hex[:8]}"

        if settings.USE_MOCK_AWS or not settings.AWS_ACCESS_KEY_ID:
            logger.info(f"[MOCK AWS] Triggered Step Function execution '{exec_id}' for record '{record_id}'")
            return {
                "executionArn": f"{settings.STEP_FUNCTION_ARN}:{exec_id}",
                "startDate": datetime.now(timezone.utc).isoformat(),
                "status": "RUNNING",
                "mock": True
            }

        try:
            sfn = boto3.client("stepfunctions", region_name=settings.AWS_REGION)
            input_data = execution_input or {
                "record_id": record_id,
                "priority_score": priority_score,
                "triggered_at": datetime.now(timezone.utc).isoformat()
            }
            response = sfn.start_execution(
                stateMachineArn=settings.STEP_FUNCTION_ARN,
                name=exec_id,
                input=json.dumps(input_data)
            )
            logger.info(f"Started Step Function execution: {response['executionArn']}")
            return {
                "executionArn": response["executionArn"],
                "startDate": response["startDate"].isoformat(),
                "status": "RUNNING",
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error starting Step Functions execution: {e}")
            raise e

    def get_s3_destination(self, record_id: str, record_type: str) -> str:
        """Returns standard S3 path destination for record backup file."""
        return f"s3://smart-hospital-backups/{record_type.lower()}/{record_id}.bak"


aws_service = AWSService()
