import os
import sys
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.config import settings
from app.core.logging import logger


class MLService:
    """Service bridge integrating backend with the trained Keras LSTM workload forecasting model

    and decision pipeline.
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.historical_data: Optional[np.ndarray] = None
        self.is_initialized = False
        self._initialize()

    def _initialize(self):
        """Loads model and fits scaler on historical training workload data."""
        try:
            from src.ml_model.preprocessing.scaler import WorkloadScaler
            from src.ml_model.preprocessing.data_loader import load_and_split_data
            import tensorflow as tf

            model_full_path = os.path.join(PROJECT_ROOT, settings.MODEL_PATH)
            data_full_path = os.path.join(PROJECT_ROOT, settings.WORKLOAD_DATA_PATH)

            if os.path.exists(data_full_path):
                train_data, _, test_data, _ = load_and_split_data(data_full_path)
                self.scaler = WorkloadScaler()
                self.scaler.fit(train_data)

                # Keep last 24 observations from test_data for inference default
                self.historical_data = test_data[-24:].flatten()
                logger.info("Successfully fitted WorkloadScaler and loaded historical data series.")
            else:
                logger.warning(f"Workload dataset not found at {data_full_path}. Initializing fallback scaler.")
                self.scaler = WorkloadScaler()
                self.scaler.min_ = np.array([0.0])
                self.scaler.max_ = np.array([10000.0])
                self.scaler.scale_ = np.array([10000.0])
                self.historical_data = np.full(24, 1200.0)

            if os.path.exists(model_full_path):
                self.model = tf.keras.models.load_model(model_full_path)
                self.is_initialized = True
                logger.info(f"Successfully loaded trained Keras LSTM model from {model_full_path}")
            else:
                logger.warning(f"Keras model file not found at {model_full_path}. Local model inference will fallback.")
        except Exception as e:
            logger.warning(f"Failed to initialize ML engine ({e}). Falling back to statistical estimation.")
            self.is_initialized = False

    def predict_workload(self, historical_24h: Optional[np.ndarray] = None) -> Tuple[float, str]:
        """Predicts workload forecast (in MB) for next 1-hour window using LSTM model."""
        if historical_24h is None:
            historical_24h = self.historical_data if self.historical_data is not None else np.full(24, 1200.0)

        if len(historical_24h) != 24:
            # Re-pad or truncate to 24
            if len(historical_24h) < 24:
                padding = np.full(24 - len(historical_24h), historical_24h[-1] if len(historical_24h) > 0 else 1000.0)
                historical_24h = np.concatenate([padding, historical_24h])
            else:
                historical_24h = historical_24h[-24:]

        if self.is_initialized and self.model is not None and self.scaler is not None:
            try:
                hw_reshaped = historical_24h.reshape(-1, 1)
                hw_scaled = self.scaler.transform(hw_reshaped)
                lstm_input = hw_scaled.reshape(1, 24, 1)

                pred_scaled = self.model.predict(lstm_input, verbose=0)
                pred_mb = float(self.scaler.inverse_transform(pred_scaled)[0, 0])
                predicted_val = max(0.0, pred_mb)
                return predicted_val, "lstm-keras-v1"
            except Exception as e:
                logger.error(f"Error executing Keras LSTM inference: {e}")

        # Statistical fallback estimation if model load failed
        last_obs = float(historical_24h[-1]) if len(historical_24h) > 0 else 1500.0
        return round(last_obs * 1.08, 2), "baseline-trend-v1"

    def execute_decision_pipeline(
        self,
        backup_records: List[Dict[str, Any]],
        historical_24h: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Executes full decision pipeline: forecasting -> priority scoring -> capacity scheduling."""
        if historical_24h is None:
            historical_24h = self.historical_data if self.historical_data is not None else np.full(24, 1200.0)

        if len(historical_24h) != 24:
            if len(historical_24h) < 24:
                padding = np.full(24 - len(historical_24h), historical_24h[-1] if len(historical_24h) > 0 else 1000.0)
                historical_24h = np.concatenate([padding, historical_24h])
            else:
                historical_24h = historical_24h[-24:]

        if self.is_initialized and self.model is not None and self.scaler is not None:
            try:
                from src.ml_model.pipeline.decision_pipeline import run_pipeline
                res = run_pipeline(
                    lstm_model=self.model,
                    scaler=self.scaler,
                    historical_workload=historical_24h,
                    backup_records=backup_records
                )
                return {
                    "predicted_workload_mb": res.predicted_workload_mb,
                    "scheduled_records": res.scheduled_records,
                    "deferred_records": res.deferred_records,
                    "total_scheduled_volume_mb": res.total_scheduled_volume_mb,
                    "remaining_capacity_mb": res.remaining_capacity_mb,
                    "model_version": "lstm-keras-v1"
                }
            except Exception as e:
                logger.error(f"Error executing decision pipeline via ML model: {e}")

        # Fallback decision pipeline execution using standalone components
        from src.ml_model.priority.priority_policy import assign_priority
        from src.ml_model.scheduler.scheduler import schedule_backups

        predicted_val, model_ver = self.predict_workload(historical_24h)
        prioritized = []
        for r in backup_records:
            rc = r.copy()
            if "priority" not in rc:
                rc["priority"] = assign_priority(rc)
            prioritized.append(rc)

        sched_res = schedule_backups(prioritized, predicted_val)
        return {
            "predicted_workload_mb": predicted_val,
            "scheduled_records": sched_res["scheduled_records"],
            "deferred_records": sched_res["deferred_records"],
            "total_scheduled_volume_mb": sched_res["scheduled_volume_mb"],
            "remaining_capacity_mb": sched_res["remaining_capacity_mb"],
            "model_version": model_ver
        }


ml_service = MLService()
