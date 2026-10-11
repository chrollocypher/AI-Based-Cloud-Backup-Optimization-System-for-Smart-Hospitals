from fastapi import APIRouter, HTTPException
from app.models.storage import (
    StorageTierTransitionRequest,
    StorageTierTransitionResponse,
    StorageCostEvaluationResponse
)
from app.services.storage_service import storage_service

router = APIRouter(prefix="/storage", tags=["Storage & Tiering"])


@router.post("/tier-transitions", response_model=StorageTierTransitionResponse)
def transition_record_tier(request: StorageTierTransitionRequest):
    """Execute a storage tier transition for an EHR record with clinical safety verification."""
    try:
        return storage_service.transition_tier(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to transition storage tier: {str(e)}")


@router.get("/cost-estimate", response_model=StorageCostEvaluationResponse)
def get_storage_cost_estimate(region: str = "us-east-1"):
    """Evaluate monthly storage & retrieval costs comparing proposed tiering against static S3 Standard baseline."""
    return storage_service.evaluate_storage_costs(pricing_region=region)
