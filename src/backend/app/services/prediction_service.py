import json
import boto3
from datetime import datetime, timezone
from typing import Optional
from app.models.prediction import (
    PredictionRequest,
    PredictionResponse,
    AccessDemandPredictionRequest,
    AccessDemandPredictionResponse,
    JointWorkloadForecastResponse
)
from app.core.config import settings
from app.core.logging import logger
from app.services.ml_service import ml_service


class PredictionService:
    def __init__(self):
        self._latest_prediction: Optional[PredictionResponse] = None
        self._latest_access_prediction: Optional[AccessDemandPredictionResponse] = None

    # --- 1. Preserved Backup Volume Forecasting ---
    def predict(self, req: PredictionRequest) -> PredictionResponse:
        """Executes backup workload forecast using the preserved LSTM model or SageMaker."""
        if settings.SAGEMAKER_ENDPOINT_NAME and not settings.USE_MOCK_AWS:
            try:
                sagemaker_runtime = boto3.client("sagemaker-runtime", region_name=settings.AWS_REGION)
                payload = json.dumps({
                    "timestamp": req.timestamp.isoformat(),
                    "data_volume": req.data_volume_mb,
                    "access_frequency": req.access_frequency
                })
                response = sagemaker_runtime.invoke_endpoint(
                    EndpointName=settings.SAGEMAKER_ENDPOINT_NAME,
                    ContentType="application/json",
                    Body=payload
                )
                result = json.loads(response["Body"].read().decode())
                predicted_val = float(result.get("predicted_backup_volume_mb", req.data_volume_mb * 1.2))
                model_ver = result.get("model_version", "sagemaker-lstm-v1")
            except Exception as e:
                logger.warning(f"SageMaker invocation failed ({e}), using local model inference.")
                predicted_val, model_ver = ml_service.predict_workload(current_volume_mb=req.data_volume_mb)
        else:
            predicted_val, model_ver = ml_service.predict_workload(current_volume_mb=req.data_volume_mb)

        pred_response = PredictionResponse(
            forecast_horizon="1 hour",
            predicted_backup_volume_mb=round(predicted_val, 2),
            confidence_interval_low=round(predicted_val * 0.9, 2),
            confidence_interval_high=round(predicted_val * 1.1, 2),
            model_version=model_ver,
            timestamp=datetime.now(timezone.utc)
        )

        self._latest_prediction = pred_response
        logger.info(f"Generated backup volume forecast: {pred_response.predicted_backup_volume_mb} MB (Model: {model_ver})")
        return pred_response

    def get_latest_prediction(self) -> PredictionResponse:
        """Returns most recent backup volume prediction or generates baseline."""
        if self._latest_prediction:
            return self._latest_prediction

        baseline_req = PredictionRequest(
            timestamp=datetime.now(timezone.utc),
            data_volume_mb=8200.0,
            access_frequency=530
        )
        return self.predict(baseline_req)

    # --- 2. New Access Demand Forecasting ---
    def predict_access_demand(self, req: AccessDemandPredictionRequest) -> AccessDemandPredictionResponse:
        """Executes access demand forecasting (event count, access volume, emergency spikes)."""
        pred_count, pred_volume, pred_emergency, model_ver = ml_service.predict_access_demand(
            current_access_count=req.current_access_count,
            current_access_volume_mb=req.current_access_volume_mb,
            recent_counts=req.recent_access_counts,
            emergency_ratio=req.emergency_context_ratio
        )

        resp = AccessDemandPredictionResponse(
            forecast_horizon="1 hour",
            predicted_access_count=pred_count,
            predicted_access_volume_mb=round(pred_volume, 2),
            predicted_emergency_count=pred_emergency,
            confidence_interval_low=round(pred_volume * 0.88, 2),
            confidence_interval_high=round(pred_volume * 1.12, 2),
            model_version=model_ver,
            timestamp=datetime.now(timezone.utc)
        )

        self._latest_access_prediction = resp
        logger.info(f"Generated access demand forecast: {pred_count} events / {pred_volume} MB (Model: {model_ver})")
        return resp

    def get_latest_access_prediction(self) -> AccessDemandPredictionResponse:
        """Returns most recent access demand prediction or generates baseline."""
        if self._latest_access_prediction:
            return self._latest_access_prediction

        baseline_req = AccessDemandPredictionRequest(
            timestamp=datetime.now(timezone.utc),
            current_access_count=1200,
            current_access_volume_mb=15400.0,
            emergency_context_ratio=0.05
        )
        return self.predict_access_demand(baseline_req)

    # --- 3. Joint Workload Forecast for Decision Engine ---
    def get_joint_workload_forecast(
        self,
        backup_req: Optional[PredictionRequest] = None,
        access_req: Optional[AccessDemandPredictionRequest] = None
    ) -> JointWorkloadForecastResponse:
        """Combines independent backup and access predictions to determine operational intensity and guidance."""
        backup_pred = self.predict(backup_req) if backup_req else self.get_latest_prediction()
        access_pred = self.predict_access_demand(access_req) if access_req else self.get_latest_access_prediction()

        # Classify joint intensity based on access demand and capacity threshold
        threshold_mb = settings.CAPACITY_THRESHOLD_MB
        backup_ratio = backup_pred.predicted_backup_volume_mb / max(threshold_mb, 1.0)

        if backup_ratio > 1.0 or access_pred.predicted_emergency_count > 50:
            intensity = "PEAK"
            recommendation = "Capacity limit reached. Throttle low-priority backups and prefetch emergency records."
        elif backup_ratio > 0.75 or access_pred.predicted_access_count > 1500:
            intensity = "HIGH"
            recommendation = "High workload expected. Transition active records to Standard tier; defer non-urgent backups."
        elif backup_ratio < 0.35 and access_pred.predicted_access_count < 600:
            intensity = "LOW"
            recommendation = "Low workload window. Ideal time for batch archival transitions and background replication."
        else:
            intensity = "NORMAL"
            recommendation = "Standard operational parameters. Maintain scheduled tier lifecycles."

        return JointWorkloadForecastResponse(
            forecast_horizon="1 hour",
            timestamp=datetime.now(timezone.utc),
            backup_forecast=backup_pred,
            access_forecast=access_pred,
            workload_intensity_level=intensity,
            recommendation=recommendation
        )


prediction_service = PredictionService()
