"""
Integration Adapter Module for Synthea-derived EHR records.
Connects the new Synthea-derived records with the existing Priority Policy and Scheduler.
Ensures seamless end-to-end execution while keeping clinical criticality rules separate from workload capacity prediction.
"""

from typing import List, Dict, Any
from src.ml_model.priority.priority_policy import assign_priority, sort_records_by_priority
from src.ml_model.scheduler.scheduler import schedule_backups
from src.ml_model.queue.pending_queue import PendingBackupQueue, run_scheduling_cycle

def adapt_synthea_record_for_scheduler(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures a Synthea EHR record has required keys for priority and scheduling.
    Synthea fields:
      - event_id -> record_id
      - data_size_mb -> data_size_mb
      - criticality -> criticality ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
    """
    adapted = record.copy()
    if 'record_id' not in adapted and 'event_id' in adapted:
        adapted['record_id'] = adapted['event_id']
    
    # Priority assignment based on criticality
    if 'priority' not in adapted:
        adapted['priority'] = assign_priority(adapted)
        
    return adapted

def run_synthea_scheduling_cycle(
    ehr_records: List[Dict[str, Any]],
    predicted_capacity_mb: float,
    queue: PendingBackupQueue
) -> Dict[str, Any]:
    """
    Runs a scheduling cycle combining new Synthea records and pending queue records
    under the predicted workload capacity.
    """
    adapted_records = [adapt_synthea_record_for_scheduler(r) for r in ehr_records]
    
    return run_scheduling_cycle(
        new_records=adapted_records,
        capacity_mb=predicted_capacity_mb,
        pending_queue=queue,
        priority_engine_sort_func=sort_records_by_priority,
        scheduler_func=schedule_backups
    )
