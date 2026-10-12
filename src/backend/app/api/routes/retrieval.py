from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.retrieval import (
    EmergencyRetrievalRequest,
    RetrievalJobResponse,
    PrefetchRequest,
    PrefetchResponse,
    RetrievalMetricsSummary
)
from app.services.retrieval_service import retrieval_service
from app.db.dynamodb import db_memory

router = APIRouter(prefix="/retrieval", tags=["Emergency Retrieval & Cache"])


@router.post("/request", response_model=RetrievalJobResponse)
def retrieve_record(request: EmergencyRetrievalRequest):
    """Execute high-priority EHR record retrieval measuring cache hits and latency SLA adherence."""
    try:
        return retrieval_service.retrieve_record(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute retrieval: {str(e)}")


@router.post("/prefetch", response_model=PrefetchResponse)
def prefetch_records(request: PrefetchRequest):
    """Proactively prefetch predicted high-demand EHR records into fast cache."""
    return retrieval_service.prefetch_records(request)


@router.get("/metrics", response_model=RetrievalMetricsSummary)
def get_retrieval_metrics():
    """Retrieve operational telemetry on retrieval latency, cache hit rate, and emergency SLA violations."""
    return retrieval_service.get_metrics()


@router.get("/jobs", response_model=List[RetrievalJobResponse])
def list_retrieval_jobs(is_emergency: Optional[bool] = Query(None)):
    """List historical retrieval jobs with optional emergency filtering."""
    raw_jobs = db_memory.list_retrievals(is_emergency=is_emergency)
    return [RetrievalJobResponse(**j) for j in raw_jobs]
