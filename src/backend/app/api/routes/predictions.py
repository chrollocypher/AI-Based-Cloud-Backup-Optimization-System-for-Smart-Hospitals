from fastapi import APIRouter
from app.models.prediction import (
    PredictionRequest,
    PredictionResponse,
    AccessDemandPredictionRequest,
    AccessDemandPredictionResponse,
    JointWorkloadForecastResponse
)
from app.services.prediction_service import prediction_service

router = APIRouter()


# --- Preserved Backup Workload Forecasting Endpoints ---
@router.post("/predictions", response_model=PredictionResponse, tags=["Predictions"])
def create_prediction(request: PredictionRequest):
    """Generate hospital backup volume prediction using preserved LSTM model."""
    return prediction_service.predict(request)


@router.post("/predictions/backup-volume", response_model=PredictionResponse, tags=["Predictions"])
def create_backup_prediction(request: PredictionRequest):
    """Explicit endpoint for next-hour backup volume forecast."""
    return prediction_service.predict(request)


@router.get("/predictions/latest", response_model=PredictionResponse, tags=["Predictions"])
def get_latest_prediction():
    """Retrieve the most recent backup volume prediction forecast."""
    return prediction_service.get_latest_prediction()


# --- New Access Demand Forecasting Endpoints ---
@router.post("/predictions/access-demand", response_model=AccessDemandPredictionResponse, tags=["Predictions"])
def create_access_prediction(request: AccessDemandPredictionRequest):
    """Generate EHR access demand prediction (access event count, volume, emergency count)."""
    return prediction_service.predict_access_demand(request)


@router.get("/predictions/access-demand/latest", response_model=AccessDemandPredictionResponse, tags=["Predictions"])
def get_latest_access_prediction():
    """Retrieve the most recent access demand prediction."""
    return prediction_service.get_latest_access_prediction()


# --- Joint Workload Forecast Endpoint ---
@router.get("/predictions/joint-forecast", response_model=JointWorkloadForecastResponse, tags=["Predictions"])
def get_joint_forecast():
    """Retrieve combined forecast integrating both backup volume and access demand for tiering decisions."""
    return prediction_service.get_joint_workload_forecast()


@router.get("/workload/forecast-latest", response_model=JointWorkloadForecastResponse, tags=["Predictions"])
def get_latest_workload_forecast():
    """Contract alias for the joint next-hour workload forecast used by the orchestrator."""
    return prediction_service.get_joint_workload_forecast()
