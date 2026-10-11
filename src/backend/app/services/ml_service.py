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
    """Service bridge integrating backend with:
    1. Preserved Keras LSTM for hourly backup-volume forecasting.
    2. Access-demand forecasting (BiLSTM / LSTM adapter for Member A).
    3. Decision pipeline for priority scheduling and tier allocation.
    """

    def __init__(self):
        self.model = None  # Preserved backup volume LSTM model
        self.access_model = None  # New access-demand model (BiLSTM/LSTM)
        self.scaler = None
        self.historical_data: Optional[np.ndarray] = None
        self.is_initialized = False
        self.is_access_initialized = False
        self._initialize()

    def _initialize(self):
        """Loads backup model, access model, and fits scaler on historical training workload data."""
        try:
            from src.ml_model.preprocessing.scaler import WorkloadScaler
            from src.ml_model.preprocessing.data_loader import load_and_split_data
            import tensorflow as tf

            model_full_path = os.path.join(PROJECT_ROOT, settings.MODEL_PATH)
            access_model_full_path = os.path.join(PROJECT_ROOT, settings.ACCESS_MODEL_PATH)
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

            # 1. Preserved Backup LSTM Checkpoint
            if os.path.exists(model_full_path):
                self.model = tf.keras.models.load_model(model_full_path)
                self.is_initialized = True
                logger.info(f"Successfully loaded preserved Keras LSTM backup model from {model_full_path}")
            else:
                logger.warning(f"Backup Keras model file not found at {model_full_path}. Backup inference will fallback.")

            # 2. Access Demand Model Checkpoint (Member A)
            if os.path.exists(access_model_full_path):
                self.access_model = tf.keras.models.load_model(access_model_full_path)
                self.is_access_initialized = True
                logger.info(f"Successfully loaded access-demand model from {access_model_full_path}")
            else:
                logger.info(f"Access model file not yet found at {access_model_full_path}. Using access adapter estimation.")
        except Exception as e:
            logger.warning(f"Failed to initialize ML engine ({e}). Falling back to statistical estimation.")
            self.is_initialized = False

    def predict_workload(self, historical_24h: Optional[np.ndarray] = None) -> Tuple[float, str]:
        """Predicts backup volume forecast (in MB) for next 1-hour window using preserved LSTM model."""
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

    def predict_access_demand(
        self,
        current_access_count: int = 1200,
        current_access_volume_mb: float = 15400.0,
        recent_counts: Optional[List[int]] = None,
        emergency_ratio: float = 0.05
    ) -> Tuple[int, float, int, str]:
        """Predicts EHR access demand (count, volume MB, emergency count) for next hour.

        Uses Member A's loaded model or adaptive autoregressive adapter.
        """
        if self.is_access_initialized and self.access_model is not None:
            try:
                # If Member A provides trained access model
                seq = np.array(recent_counts if recent_counts else [current_access_count] * 24, dtype=float)
                if len(seq) < 24:
                    seq = np.pad(seq, (24 - len(seq), 0), mode="edge")
                else:
                    seq = seq[-24:]
                inp = seq.reshape(1, 24, 1)
                pred = self.access_model.predict(inp, verbose=0)
                pred_count = max(0, int(round(float(pred[0, 0]))))
                pred_volume = round(pred_count * (current_access_volume_mb / max(current_access_count, 1)), 2)
                pred_emergency = max(0, int(round(pred_count * emergency_ratio)))
                return pred_count, pred_volume, pred_emergency, "bilstm-access-ml-v1"
            except Exception as e:
                logger.warning(f"Error in access-demand model inference: {e}. Falling back to adapter.")

        # Adaptive autoregressive estimation
        if recent_counts and len(recent_counts) >= 3:
            weights = np.linspace(0.5, 1.0, len(recent_counts[-6:]))
            weights /= weights.sum()
            avg_count = float(np.dot(recent_counts[-6:], weights))
            growth = 1.02 if recent_counts[-1] > recent_counts[-2] else 0.98
            pred_count = max(50, int(round(avg_count * growth)))
        else:
            pred_count = max(50, int(round(current_access_count * 1.05)))

        pred_volume = round(pred_count * (current_access_volume_mb / max(current_access_count, 1)), 2)
        pred_emergency = max(0, int(round(pred_count * emergency_ratio)))
        return pred_count, pred_volume, pred_emergency, "access-demand-adapter-v1"

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
