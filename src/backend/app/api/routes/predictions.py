from fastapi import APIRouter
from app.models.prediction import PredictionRequest, PredictionResponse
from app.services.prediction_service import prediction_service

router = APIRouter()


@router.post("/predictions", response_model=PredictionResponse, tags=["Predictions"])
def create_prediction(request: PredictionRequest):
    """Generate hospital data workload prediction using LSTM model."""
    return prediction_service.predict(request)


@router.get("/predictions/latest", response_model=PredictionResponse, tags=["Predictions"])
def get_latest_prediction():
    """Retrieve the most recent workload prediction forecast."""
    return prediction_service.get_latest_prediction()
