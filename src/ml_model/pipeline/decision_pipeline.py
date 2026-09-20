"""
Decision pipeline module.
Integrates LSTM workload forecasting, Priority Engine, and Scheduler.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np

# Import existing components
from src.ml_model.priority.priority_policy import assign_priority
from src.ml_model.scheduler.scheduler import schedule_backups

@dataclass
class PipelineResult:
    predicted_workload_mb: float
    scheduled_records: List[Dict[str, Any]]
    deferred_records: List[Dict[str, Any]]
    total_scheduled_volume_mb: float
    remaining_capacity_mb: float

def run_pipeline(
    lstm_model: Any,
    scaler: Any,
    historical_workload: np.ndarray,
    backup_records: List[Dict[str, Any]]
) -> PipelineResult:
    """
    Executes the complete AI decision pipeline.
    
    Args:
        lstm_model: A trained Keras LSTM model.
        scaler: A fitted WorkloadScaler instance.
        historical_workload (np.ndarray): 1D array of exactly 24 past observations (MB).
        backup_records (List[Dict]): List of backup records to be scheduled.
        
    Returns:
        PipelineResult: An object containing the schedule and metrics.
    """
    if len(historical_workload) != 24:
        raise ValueError("historical_workload must contain exactly 24 observations.")
        
    # STEP 1: FORECAST
    # Shape historical data to (24, 1) and scale
    hw_reshaped = historical_workload.reshape(-1, 1)
    hw_scaled = scaler.transform(hw_reshaped)
    
    # LSTM expects (batch, timesteps, features) -> (1, 24, 1)
    lstm_input = hw_scaled.reshape(1, 24, 1)
    
    # Predict and inverse transform
    pred_scaled = lstm_model.predict(lstm_input, verbose=0)
    pred_mb = scaler.inverse_transform(pred_scaled)[0, 0]
    predicted_capacity_mb = float(max(0.0, pred_mb))  # Ensure non-negative
    
    # STEP 2: PRIORITY ASSIGNMENT
    prioritized_records = []
    for record in backup_records:
        record_copy = record.copy()
        if "priority" not in record_copy:
            record_copy["priority"] = assign_priority(record_copy)
        prioritized_records.append(record_copy)
        
    # STEP 3: SCHEDULING
    schedule_result = schedule_backups(prioritized_records, predicted_capacity_mb)
    
    # STEP 4: RETURN RESULT
    return PipelineResult(
        predicted_workload_mb=predicted_capacity_mb,
        scheduled_records=schedule_result["scheduled_records"],
        deferred_records=schedule_result["deferred_records"],
        total_scheduled_volume_mb=schedule_result["scheduled_volume_mb"],
        remaining_capacity_mb=schedule_result["remaining_capacity_mb"]
    )
