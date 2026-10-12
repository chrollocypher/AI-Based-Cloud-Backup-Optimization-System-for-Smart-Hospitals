from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from app.services.aws_service import aws_service

router = APIRouter(prefix="/orchestration", tags=["AWS Step Functions Orchestration"])


@router.post("/trigger-pipeline")
def trigger_storage_pipeline(input_data: Optional[Dict[str, Any]] = None):
    """Trigger the end-to-end Step Functions storage optimization pipeline:

    Forecast -> Decide Tiers -> Execute S3 Transitions -> Publish Metrics.
    """
    try:
        return aws_service.execute_storage_pipeline(execution_input=input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute pipeline: {str(e)}")


@router.get("/executions/{execution_id}")
def get_execution_details(execution_id: str):
    """Retrieve execution output and state machine trace for a specific execution."""
    execution = aws_service.get_pipeline_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found.")
    return execution


@router.get("/executions")
def list_executions():
    """List all pipeline executions."""
    return aws_service.list_pipeline_executions()
