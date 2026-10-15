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

# Trained Synthea LSTMs use a 14-step lookback (see synthea_*_train_stats.json).
LOOKBACK = 14


class MLService:
    """Service bridge integrating backend with:
    1. Preserved Keras LSTM for backup-volume forecasting.
    2. Access-demand forecasting (LSTM on access_workload_mb).
    3. Decision pipeline for priority scheduling and capacity allocation.
    """

    def __init__(self):
        self.model = None
        self.access_model = None
        self.scaler = None
        self.access_scaler = None
        self.historical_data: Optional[np.ndarray] = None
        self.historical_access: Optional[np.ndarray] = None
        self.is_initialized = False
        self.is_access_initialized = False
        self._initialize()

    @staticmethod
    def _fit_lookback(series, lookback: int = LOOKBACK, default: float = 1200.0) -> np.ndarray:
        arr = np.asarray(series if series is not None else [], dtype=float).flatten()
        if len(arr) == 0:
            return np.full(lookback, default)
        if len(arr) < lookback:
            pad = np.full(lookback - len(arr), arr[0])
            return np.concatenate([pad, arr])
        return arr[-lookback:]

    def _initialize(self):
        """Loads backup model, access model, scalers, and historical workload series."""
        try:
            from src.ml_model.synthetic_ehr.data_loader import SyntheaWorkloadScaler

            backup_scaler_path = os.path.join(PROJECT_ROOT, "src/ml_model/synthetic_ehr/models/synthea_backup_scaler.json")
            if os.path.exists(backup_scaler_path):
                self.scaler = SyntheaWorkloadScaler().load(backup_scaler_path)
                logger.info("Successfully loaded Synthea backup scaler from JSON.")

            access_scaler_path = os.path.join(PROJECT_ROOT, "src/ml_model/synthetic_ehr/models/synthea_access_scaler.json")
            if os.path.exists(access_scaler_path):
                self.access_scaler = SyntheaWorkloadScaler().load(access_scaler_path)
                logger.info("Successfully loaded Synthea access scaler from JSON.")
        except Exception as e:
            logger.warning(f"Could not load custom scaler: {e}")
            if self.scaler is None:
                try:
                    from archive.legacy_custom_model.src.ml_model.preprocessing.scaler import WorkloadScaler
                    self.scaler = WorkloadScaler()
                except Exception:
                    pass

        try:
            data_full_path = os.path.join(PROJECT_ROOT, settings.WORKLOAD_DATA_PATH)
            if not os.path.exists(data_full_path):
                data_full_path = os.path.join(PROJECT_ROOT, "dataset/synthea/processed/synthea_hourly_workload.csv")
            if os.path.exists(data_full_path):
                import pandas as pd
                df = pd.read_csv(data_full_path)
                backup_col = "backup_workload_mb" if "backup_workload_mb" in df.columns else df.columns[-1]
                self.historical_data = df[backup_col].tail(LOOKBACK).values.astype(float)
                if "access_workload_mb" in df.columns:
                    self.historical_access = df["access_workload_mb"].tail(LOOKBACK).values.astype(float)
                logger.info(f"Loaded {len(self.historical_data)} historical workload points from {data_full_path}")
            else:
                self.historical_data = np.full(LOOKBACK, 1200.0)
                self.historical_access = np.full(LOOKBACK, 15400.0)
        except Exception as e:
            logger.warning(f"Could not load historical workload data: {e}")
            self.historical_data = np.full(LOOKBACK, 1200.0)
            self.historical_access = np.full(LOOKBACK, 15400.0)

        try:
            import tensorflow as tf
            model_full_path = os.path.join(PROJECT_ROOT, settings.MODEL_PATH)
            if not os.path.exists(model_full_path):
                model_full_path = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/src/ml_model/models/best_lstm_model.keras")

            if os.path.exists(model_full_path):
                self.model = tf.keras.models.load_model(model_full_path)
                self.is_initialized = True
                logger.info(f"Successfully loaded Keras LSTM backup model from {model_full_path}")

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
        """Predicts backup volume forecast (in MB) for the next window using the Synthea LSTM."""
        historical = self._fit_lookback(
            historical_24h if historical_24h is not None else self.historical_data,
            default=1200.0,
        )

        if self.is_initialized and self.model is not None and self.scaler is not None:
            try:
                hw_reshaped = historical.reshape(-1, 1)
                hw_scaled = self.scaler.transform(hw_reshaped)
                lstm_input = hw_scaled.reshape(1, LOOKBACK, 1)

                pred_scaled = self.model.predict(lstm_input, verbose=0)
                pred_mb = float(self.scaler.inverse_transform(pred_scaled)[0, 0])
                predicted_val = max(0.0, pred_mb)
                if predicted_val > 0.0:
                    return predicted_val, "lstm-keras-v1"
            except Exception as e:
                logger.error(f"Error executing Keras LSTM inference: {e}")

        if current_volume_mb is not None and current_volume_mb > 0:
            return round(current_volume_mb * 1.05, 2), "trend-projection-v1"

        non_zeros = historical[historical > 0]
        base_val = float(historical[-1]) if (len(historical) > 0 and historical[-1] > 0) else (float(np.mean(non_zeros)) if len(non_zeros) > 0 else 1250.0)
        return round(base_val * 1.08, 2), "baseline-trend-v1"

    def predict_access_demand(
        self,
        current_access_count: int = 1200,
        current_access_volume_mb: float = 15400.0,
        recent_counts: Optional[List[int]] = None,
        emergency_ratio: float = 0.05
    ) -> Tuple[int, float, int, str]:
        """Predicts EHR access demand (count, volume MB, emergency count) for next hour.

        The Synthea access LSTM forecasts access_workload_mb; event count is derived from mean size.
        """
        avg_size = current_access_volume_mb / max(current_access_count, 1)

        if self.is_access_initialized and self.access_model is not None and self.access_scaler is not None:
            try:
                if recent_counts:
                    seq = np.array([c * avg_size for c in recent_counts], dtype=float)
                elif self.historical_access is not None:
                    seq = np.array(self.historical_access, dtype=float)
                else:
                    seq = np.full(LOOKBACK, current_access_volume_mb, dtype=float)
                seq = self._fit_lookback(seq, default=current_access_volume_mb)
                scaled = self.access_scaler.transform(seq.reshape(-1, 1))
                pred = self.access_model.predict(scaled.reshape(1, LOOKBACK, 1), verbose=0)
                pred_volume = max(0.0, float(self.access_scaler.inverse_transform(pred)[0, 0]))
                pred_count = max(0, int(round(pred_volume / max(avg_size, 1e-6))))
                pred_emergency = max(0, int(round(pred_count * emergency_ratio)))
                return pred_count, round(pred_volume, 2), pred_emergency, "lstm-access-ml-v1"
            except Exception as e:
                logger.warning(f"Error in access-demand model inference: {e}. Falling back to adapter.")

        if recent_counts and len(recent_counts) >= 3:
            weights = np.linspace(0.5, 1.0, len(recent_counts[-6:]))
            weights /= weights.sum()
            avg_count = float(np.dot(recent_counts[-6:], weights))
            growth = 1.02 if recent_counts[-1] > recent_counts[-2] else 0.98
            pred_count = max(50, int(round(avg_count * growth)))
        else:
            pred_count = max(50, int(round(current_access_count * 1.05)))

        pred_volume = round(pred_count * avg_size, 2)
        pred_emergency = max(0, int(round(pred_count * emergency_ratio)))
        return pred_count, pred_volume, pred_emergency, "access-demand-adapter-v1"

    def execute_decision_pipeline(
        self,
        backup_records: List[Dict[str, Any]],
        historical_24h: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Executes full decision pipeline: forecasting -> priority scoring -> capacity scheduling."""
        from app.scheduler.priority_engine import prioritize_records
        from src.ml_model.synthetic_ehr.integration_adapter import adapt_synthea_record_for_scheduler
        from src.ml_model.priority.priority_policy import assign_priority
        from src.ml_model.scheduler.scheduler import schedule_backups

        predicted_val, model_ver = self.predict_workload(historical_24h)
        adapted = [adapt_synthea_record_for_scheduler(r) for r in backup_records]
        prioritized = prioritize_records(adapted)

        for rc in prioritized:
            if not isinstance(rc.get("priority"), int):
                try:
                    rc["priority"] = assign_priority(rc)
                except Exception:
                    rc["priority"] = 2

        total_needed = sum(float(r.get("data_size_mb", 10.0)) for r in prioritized)
        effective_capacity = min(settings.CAPACITY_THRESHOLD_MB, max(predicted_val, total_needed)) if prioritized else settings.CAPACITY_THRESHOLD_MB
        if predicted_val > settings.CAPACITY_THRESHOLD_MB:
            effective_capacity = settings.CAPACITY_THRESHOLD_MB

        sched_res = schedule_backups(prioritized, effective_capacity) if prioritized else {
            "scheduled_records": [],
            "deferred_records": [],
            "scheduled_volume_mb": 0.0,
            "remaining_capacity_mb": effective_capacity,
        }
        return {
            "predicted_workload_mb": predicted_val,
            "scheduled_records": sched_res["scheduled_records"],
            "deferred_records": sched_res["deferred_records"],
            "total_scheduled_volume_mb": sched_res["scheduled_volume_mb"],
            "remaining_capacity_mb": sched_res["remaining_capacity_mb"],
            "model_version": model_ver
        }


ml_service = MLService()
