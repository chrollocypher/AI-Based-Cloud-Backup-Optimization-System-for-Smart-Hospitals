import json
import uuid
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger


class AWSService:
    """Service layer isolating AWS Boto3 API interactions for Step Functions, S3, and DynamoDB."""

    def __init__(self):
        self._pipeline_executions: Dict[str, Dict[str, Any]] = {}

    def trigger_step_function(self, record_id: str, priority_score: float, execution_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Triggers legacy Step Functions state machine execution for backup processing."""
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

    def execute_storage_pipeline(self, execution_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes full multi-step state machine pipeline:

        Forecast -> Decide Tiers -> S3 Transitions -> Metrics & Audit.
        In local/mock mode, runs task handlers sequentially with identical event propagation.
        In live mode, triggers AWS Step Functions state machine.
        """
        exec_id = f"pipeline-{uuid.uuid4().hex[:8]}"
        start_time = datetime.now(timezone.utc)
        payload = execution_input or {}

        if not settings.USE_MOCK_AWS and settings.AWS_ACCESS_KEY_ID:
            try:
                sfn = boto3.client("stepfunctions", region_name=settings.AWS_REGION)
                response = sfn.start_execution(
                    stateMachineArn=settings.STEP_FUNCTION_ARN,
                    name=exec_id,
                    input=json.dumps(payload)
                )
                exec_record = {
                    "execution_id": exec_id,
                    "executionArn": response["executionArn"],
                    "started_at": response["startDate"].isoformat(),
                    "status": "RUNNING",
                    "mode": "AWS_LIVE"
                }
                self._pipeline_executions[exec_id] = exec_record
                return exec_record
            except Exception as e:
                logger.warning(f"Failed to start live Step Functions ({e}), executing simulated pipeline.")

        # Local High-Fidelity Step Functions Simulation
        from aws.lambdas import forecast_task, tier_decision_task, s3_transition_task, metrics_task

        # Step 1: Forecast Task
        step1_res = forecast_task.lambda_handler(payload, None)
        pipeline_event = {"forecast": step1_res}

        # Step 2: Tier Decision Task
        step2_res = tier_decision_task.lambda_handler(pipeline_event, None)
        pipeline_event["decisions"] = step2_res

        # Step 3: S3 Transition Task
        step3_res = s3_transition_task.lambda_handler(pipeline_event, None)
        pipeline_event["transitions_result"] = step3_res

        # Step 4: Metrics Task
        step4_res = metrics_task.lambda_handler(pipeline_event, None)
        pipeline_event["metrics_result"] = step4_res

        exec_record = {
            "execution_id": exec_id,
            "executionArn": f"arn:aws:states:us-east-1:123456789012:execution:SmartHospitalStoragePipeline:{exec_id}",
            "started_at": start_time.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCEEDED",
            "mode": "SIMULATION",
            "forecast_intensity": step1_res.get("workload_intensity_level"),
            "transitions_executed": step3_res.get("transitions_executed_count", 0),
            "output": pipeline_event
        }
        self._pipeline_executions[exec_id] = exec_record
        logger.info(f"Completed pipeline execution {exec_id} with {exec_record['transitions_executed']} transitions.")
        return exec_record

    def get_pipeline_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a pipeline execution."""
        return self._pipeline_executions.get(execution_id)

    def list_pipeline_executions(self) -> List[Dict[str, Any]]:
        """Lists historical pipeline executions."""
        return list(self._pipeline_executions.values())

    def get_s3_destination(self, record_id: str, record_type: str) -> str:
        """Returns standard S3 path destination for record backup file."""
        return f"s3://smart-hospital-backups/{record_type.lower()}/{record_id}.bak"


aws_service = AWSService()
