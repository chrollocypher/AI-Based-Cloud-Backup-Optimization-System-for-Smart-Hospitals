from fastapi import APIRouter
from typing import Dict, Any, List
from app.models.dashboard import MonitoringStatusResponse
from app.services.dashboard_service import dashboard_service
from app.services.monitoring_service import monitoring_service

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Observability"])


@router.get("/status", response_model=MonitoringStatusResponse)
def get_monitoring_status():
    """Retrieve backend and infrastructure operational monitoring status."""
    return dashboard_service.get_monitoring_status()


@router.get("/system-telemetry")
def get_system_telemetry():
    """Retrieve all 7 research evaluation metrics (latency, availability, costs, cache hits, backup success, SLA, accuracy)."""
    return monitoring_service.get_system_telemetry()


@router.post("/cloudwatch/publish")
def publish_cloudwatch_metrics():
    """Publish current operational telemetry to AWS CloudWatch custom metrics namespace."""
    return monitoring_service.publish_cloudwatch_metrics()


@router.get("/cloudwatch/alarms")
def get_cloudwatch_alarms():
    """Inspect CloudWatch alarms and clinical SLA threshold breach alerts."""
    return monitoring_service.get_alarms_status()
