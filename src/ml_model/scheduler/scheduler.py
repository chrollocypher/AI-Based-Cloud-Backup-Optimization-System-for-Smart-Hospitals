"""
Backup scheduling policy module for Smart Hospital Backup Optimization.
This module defines deterministic, explainable rules for scheduling backup 
records based on their priority and the available capacity.
"""
from typing import Dict, List, Any

class InvalidInputError(ValueError):
    """Exception raised for invalid scheduler inputs."""
    pass

def validate_record(record: Dict[str, Any]) -> None:
    """Validates if a record contains all required fields for scheduling."""
    required_keys = {"record_id", "data_size_mb", "criticality", "priority"}
    missing_keys = required_keys - record.keys()
    if missing_keys:
        raise InvalidInputError(f"Record is missing required keys: {missing_keys}")
    
    if not isinstance(record["data_size_mb"], (int, float)) or record["data_size_mb"] <= 0:
        raise InvalidInputError(f"Invalid data_size_mb for record {record.get('record_id')}: must be a positive number.")
        
    if not isinstance(record["priority"], int):
        raise InvalidInputError(f"Invalid priority for record {record.get('record_id')}: must be an integer.")

def schedule_backups(
    records: List[Dict[str, Any]], 
    capacity_mb: float
) -> Dict[str, Any]:
    """
    Schedules backup records based on priority and available capacity.
    
    Args:
        records (List[Dict[str, Any]]): List of backup records to schedule.
        capacity_mb (float): Predicted available backup capacity in MB.
        
    Returns:
        Dict[str, Any]: A dictionary containing the scheduling results:
            - scheduled_records: List of records that fit within capacity.
            - deferred_records: List of records that did not fit.
            - scheduled_volume_mb: Total volume of scheduled records.
            - remaining_capacity_mb: Remaining capacity after scheduling.
    """
    if not isinstance(capacity_mb, (int, float)) or capacity_mb < 0:
        raise InvalidInputError("Capacity must be a non-negative number.")
        
    for record in records:
        validate_record(record)
        
    # Sort primarily by priority descending, secondarily by record_id ascending for deterministic behavior
    sorted_records = sorted(records, key=lambda x: (-x["priority"], x["record_id"]))
    
    scheduled_records = []
    deferred_records = []
    current_volume = 0.0
    
    for record in sorted_records:
        size = float(record["data_size_mb"])
        if current_volume + size <= capacity_mb:
            scheduled_records.append(record)
            current_volume += size
        else:
            deferred_records.append(record)
            
    return {
        "scheduled_records": scheduled_records,
        "deferred_records": deferred_records,
        "scheduled_volume_mb": current_volume,
        "remaining_capacity_mb": capacity_mb - current_volume
    }
