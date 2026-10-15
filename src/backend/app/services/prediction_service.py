import json
import boto3
from datetime import datetime, timezone
from typing import Optional
from app.models.prediction import PredictionRequest, PredictionResponse
from app.core.config import settings
from app.core.logging import logger


class PredictionService:
    def __init__(self):
        self._latest_prediction: Optional[PredictionResponse] = None

    def predict(self, req: PredictionRequest) -> PredictionResponse:
        """Executes LSTM workload forecast via SageMaker or local model fallback."""
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
                predicted_val, model_ver = self._local_lstm_inference(req)
        else:
            predicted_val, model_ver = self._local_lstm_inference(req)

        pred_response = PredictionResponse(
            forecast_horizon="1 hour",
            predicted_backup_volume_mb=round(predicted_val, 2),
            confidence_interval_low=round(predicted_val * 0.9, 2),
            confidence_interval_high=round(predicted_val * 1.1, 2),
            model_version=model_ver,
            timestamp=datetime.now(timezone.utc)
        )

        self._latest_prediction = pred_response
        logger.info(f"Generated workload prediction: {pred_response.predicted_backup_volume_mb} MB (Model: {model_ver})")
        return pred_response

    def _local_lstm_inference(self, req: PredictionRequest) -> tuple[float, str]:
        """Local LSTM mock / trend estimation engine."""
        # Forecast workload trend based on current data volume & access frequency
        growth_factor = 1.15 + (req.access_frequency / 2000.0)
        predicted_volume = req.data_volume_mb * growth_factor
        return predicted_volume, "local-lstm-v1"

    def get_latest_prediction(self) -> PredictionResponse:

        """Returns most recent prediction or generates default baseline forecast."""
        if self._latest_prediction:
            return self._latest_prediction

        # Default baseline prediction if none generated yet
        baseline_req = PredictionRequest(
            timestamp=datetime.now(timezone.utc),
            data_volume_mb=8200.0,
            access_frequency=530
        )
        return self.predict(baseline_req)


prediction_service = PredictionService()
