"""
Pending queue module for multi-cycle backup scheduling.
"""
from typing import Dict, List, Any

class PendingBackupQueue:
    """
    A persistent queue for backup records that were deferred in previous scheduling cycles.
    """
    
    def __init__(self) -> None:
        self._queue: Dict[str, Dict[str, Any]] = {}
        
    def add_deferred(self, records: List[Dict[str, Any]]) -> None:
        """
        Add deferred records to the pending queue.
        Preserves original priority and criticality.
        Prevents duplicate record IDs.
        
        Args:
            records: List of deferred backup records.
        """
        for record in records:
            record_id = record["record_id"]
            if record_id not in self._queue:
                self._queue[record_id] = record.copy()
                
    def get_pending(self) -> List[Dict[str, Any]]:
        """
        Return the current pending records.
        
        Returns:
            List of pending backup records.
        """
        return list(self._queue.values())
        
    def remove_scheduled(self, records: List[Dict[str, Any]]) -> None:
        """
        Remove successfully scheduled records from the pending queue.
        
        Args:
            records: List of scheduled backup records.
        """
        for record in records:
            record_id = record["record_id"]
            if record_id in self._queue:
                del self._queue[record_id]
                
    def clear(self) -> None:
        """
        Clear the queue when required.
        """
        self._queue.clear()
        
    def contains(self, record_id: str) -> bool:
        """
        Check whether a record is already pending.
        
        Args:
            record_id: ID of the record to check.
            
        Returns:
            True if the record is pending, False otherwise.
        """
        return record_id in self._queue


def run_scheduling_cycle(
    new_records: List[Dict[str, Any]], 
    capacity_mb: float, 
    pending_queue: PendingBackupQueue,
    priority_engine_sort_func: Any,
    scheduler_func: Any
) -> Dict[str, Any]:
    """
    Executes a single scheduling cycle, combining new records and pending records.
    
    Args:
        new_records: List of new backup records.
        capacity_mb: Available capacity for this cycle.
        pending_queue: The persistent pending queue instance.
        priority_engine_sort_func: Function to sort records by priority.
        scheduler_func: Function to schedule backups.
        
    Returns:
        Dict containing scheduled_records, deferred_records, and pending_queue_after.
    """
    # 1. Combine new records and pending records
    pending_records = pending_queue.get_pending()
    
    # Avoid duplicates if a new record is somehow already pending
    pending_ids = {r["record_id"] for r in pending_records}
    unique_new_records = [r for r in new_records if r["record_id"] not in pending_ids]
    
    all_records = pending_records + unique_new_records
    
    # 2. Priority Engine
    sorted_records = priority_engine_sort_func(all_records)
    
    # 3. Scheduler
    results = scheduler_func(sorted_records, capacity_mb)
    
    scheduled = results["scheduled_records"]
    deferred = results["deferred_records"]
    
    # 4. Update Queue
    pending_queue.remove_scheduled(scheduled)
    pending_queue.add_deferred(deferred)
    
    return {
        "scheduled_records": scheduled,
        "deferred_records": deferred,
        "pending_queue_after": pending_queue.get_pending()
    }
