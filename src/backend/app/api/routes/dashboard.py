from fastapi import APIRouter
from typing import List
from app.models.dashboard import DashboardSummaryResponse, WorkloadPoint
from app.services.dashboard_service import dashboard_service

router = APIRouter()


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse, tags=["Dashboard"])
def get_dashboard_summary():
    """Retrieve operational dashboard summary metrics for frontend UI."""
    return dashboard_service.get_summary()


@router.get("/dashboard/workload", response_model=List[WorkloadPoint], tags=["Dashboard"])
def get_dashboard_workload():
    """Retrieve actual vs. predicted workload time-series dataset for charts."""
    return dashboard_service.get_workload_timeseries()
