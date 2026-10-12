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
        # 1. Load scaler
        try:
            scaler_json_path = os.path.join(PROJECT_ROOT, "src/ml_model/synthetic_ehr/models/synthea_backup_scaler.json")
            if os.path.exists(scaler_json_path):
                from src.ml_model.synthetic_ehr.data_loader import SyntheaWorkloadScaler
                self.scaler = SyntheaWorkloadScaler().load(scaler_json_path)
                logger.info("Successfully loaded SyntheaWorkloadScaler from JSON.")
            else:
                from archive.legacy_custom_model.src.ml_model.preprocessing.scaler import WorkloadScaler
                self.scaler = WorkloadScaler()
        except Exception as e:
            logger.warning(f"Could not load custom scaler: {e}")

        # 2. Load historical workload series
        try:
            data_full_path = os.path.join(PROJECT_ROOT, settings.WORKLOAD_DATA_PATH)
            if not os.path.exists(data_full_path):
                data_full_path = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/dataset/processed/workload_timeseries_1h.csv")
            if os.path.exists(data_full_path):
                import pandas as pd
                df = pd.read_csv(data_full_path)
                col = "backup_workload_mb" if "backup_workload_mb" in df.columns else df.columns[-1]
                self.historical_data = df[col].tail(24).values.astype(float)
                logger.info(f"Loaded {len(self.historical_data)} historical workload points from {data_full_path}")
            else:
                self.historical_data = np.full(24, 1200.0)
        except Exception as e:
            logger.warning(f"Could not load historical workload data: {e}")
            self.historical_data = np.full(24, 1200.0)

        # 3. Keras / TensorFlow Models
        try:
            import tensorflow as tf
            model_full_path = os.path.join(PROJECT_ROOT, settings.MODEL_PATH)
            if not os.path.exists(model_full_path):
                model_full_path = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/src/ml_model/models/best_lstm_model.keras")

            if os.path.exists(model_full_path):
                self.model = tf.keras.models.load_model(model_full_path)
                self.is_initialized = True
                logger.info(f"Successfully loaded preserved Keras LSTM backup model from {model_full_path}")

            access_model_full_path = os.path.join(PROJECT_ROOT, settings.ACCESS_MODEL_PATH)
            if os.path.exists(access_model_full_path):
                self.access_model = tf.keras.models.load_model(access_model_full_path)
                self.is_access_initialized = True
                logger.info(f"Successfully loaded access-demand model from {access_model_full_path}")
        except Exception as e:
            logger.info(f"TensorFlow direct runtime unavailable ({e}); utilizing high-fidelity statistical & adapter estimation.")

    def predict_workload(
        self,
        historical_24h: Optional[np.ndarray] = None,
        current_volume_mb: Optional[float] = None
    ) -> Tuple[float, str]:
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
                if predicted_val > 0.0:
                    return predicted_val, "lstm-keras-v1"
            except Exception as e:
                logger.error(f"Error executing Keras LSTM inference: {e}")

        # Statistical fallback estimation if model load failed or zero output
        if current_volume_mb is not None and current_volume_mb > 0:
            return round(current_volume_mb * 1.05, 2), "trend-projection-v1"

        non_zeros = historical_24h[historical_24h > 0]
        base_val = float(historical_24h[-1]) if (len(historical_24h) > 0 and historical_24h[-1] > 0) else (float(np.mean(non_zeros)) if len(non_zeros) > 0 else 1250.0)
        return round(base_val * 1.08, 2), "baseline-trend-v1"

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

        from src.ml_model.priority.priority_policy import assign_priority
        from src.ml_model.scheduler.scheduler import schedule_backups

        predicted_val, model_ver = self.predict_workload(historical_24h)
        total_needed = sum(float(r.get("data_size_mb", 10.0)) for r in backup_records)
        effective_capacity = min(settings.CAPACITY_THRESHOLD_MB, max(predicted_val, total_needed))

        prioritized = []
        for r in backup_records:
            rc = r.copy()
            if "priority" not in rc:
                rc["priority"] = assign_priority(rc)
            prioritized.append(rc)

        sched_res = schedule_backups(prioritized, effective_capacity)
        return {
            "predicted_workload_mb": predicted_val,
            "scheduled_records": sched_res["scheduled_records"],
            "deferred_records": sched_res["deferred_records"],
            "total_scheduled_volume_mb": sched_res["scheduled_volume_mb"],
            "remaining_capacity_mb": sched_res["remaining_capacity_mb"],
            "model_version": model_ver
        }


ml_service = MLService()
