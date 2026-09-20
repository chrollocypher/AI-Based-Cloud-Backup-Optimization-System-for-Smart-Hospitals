"""
Priority policy module for Smart Hospital Backup Optimization.
This module defines deterministic, explainable rules for assigning priority to backup records based on their criticality.
"""
from typing import Dict, List, Any

# Priority Mapping Policy
PRIORITY_POLICY: Dict[str, int] = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}

class InvalidCriticalityError(ValueError):
    """Exception raised for invalid criticality values."""
    pass

def validate_criticality(criticality: str) -> None:
    """
    Validates if a given criticality string is supported by the policy.
    
    Args:
        criticality (str): The criticality level.
        
    Raises:
        InvalidCriticalityError: If the criticality is not one of the allowed values.
    """
    if not isinstance(criticality, str) or criticality.upper() not in PRIORITY_POLICY:
        raise InvalidCriticalityError(
            f"Invalid criticality: '{criticality}'. "
            f"Allowed values are: {', '.join(PRIORITY_POLICY.keys())}"
        )

def assign_priority(record: Dict[str, Any]) -> int:
    """
    Assigns a numeric priority to a backup record based on its criticality.
    
    Args:
        record (Dict[str, Any]): A dictionary representing a backup record, 
                                 which must contain a 'criticality' key.
                                 
    Returns:
        int: The numeric priority (4 for CRITICAL, down to 1 for LOW).
        
    Raises:
        KeyError: If 'criticality' key is missing from the record.
        InvalidCriticalityError: If the 'criticality' value is invalid.
    """
    if "criticality" not in record:
        raise KeyError("Record must contain a 'criticality' field.")
        
    criticality = record["criticality"]
    validate_criticality(criticality)
    
    return PRIORITY_POLICY[criticality.upper()]

def sort_records_by_priority(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sorts a list of backup records from highest priority to lowest priority.
    Records that lack priority will have it assigned.
    
    Args:
        records (List[Dict[str, Any]]): A list of backup records.
        
    Returns:
        List[Dict[str, Any]]: A new list of records sorted by priority descending.
    """
    # Ensure all records have a 'priority' assigned
    records_with_priority = []
    for record in records:
        record_copy = record.copy()
        if "priority" not in record_copy:
            record_copy["priority"] = assign_priority(record_copy)
        records_with_priority.append(record_copy)
        
    # Sort by priority descending
    return sorted(records_with_priority, key=lambda x: x["priority"], reverse=True)
