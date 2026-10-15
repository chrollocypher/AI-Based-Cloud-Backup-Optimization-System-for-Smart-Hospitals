from fastapi import APIRouter
from app.models.dashboard import MonitoringStatusResponse
from app.services.dashboard_service import dashboard_service

router = APIRouter()


@router.get("/monitoring/status", response_model=MonitoringStatusResponse, tags=["Monitoring"])
def get_monitoring_status():
    """Retrieve backend and infrastructure operational monitoring status."""
    return dashboard_service.get_monitoring_status()
