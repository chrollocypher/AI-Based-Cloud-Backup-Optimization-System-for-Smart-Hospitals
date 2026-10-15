from datetime import datetime, timezone
from typing import List, Optional
from app.models.schedule import ScheduleResponse, ScheduleItem
from app.services.record_service import record_service
from app.services.prediction_service import prediction_service
from app.scheduler.priority_engine import prioritize_records
from app.core.config import settings
from app.core.logging import logger


class SmartScheduler:
    def __init__(self):
        self._last_schedule: Optional[ScheduleResponse] = None

    def generate_schedule(self) -> ScheduleResponse:
        """Generates backup schedule based on LSTM predictions, priority scoring, and capacity limits."""
        # 1. Fetch pending records
        all_records = [r.model_dump() for r in record_service.list_records()]
        pending_records = [r for r in all_records if r.get("backup_status") == "PENDING"]

        # 2. Sort by Priority Engine
        prioritized = prioritize_records(pending_records)

        # 3. Get latest workload forecast
        prediction = prediction_service.get_latest_prediction()
        predicted_mb = prediction.predicted_backup_volume_mb
        threshold_mb = settings.CAPACITY_THRESHOLD_MB
        is_exceeded = predicted_mb > threshold_mb

        schedule_items: List[ScheduleItem] = []
        now_count = 0
        deferred_count = 0

        accumulated_mb = 0.0

        for rec in prioritized:
            crit = rec.get("criticality", "MEDIUM")
            size = rec.get("data_size_mb", 10.0)

            if is_exceeded:
                # Capacity limit exceeded - enforce strict priority throttling
                if crit == "CRITICAL":
                    action = "BACKUP_NOW"
                    reason = "Critical hospital record - immediate backup required"
                    now_count += 1
                elif crit == "HIGH" and (accumulated_mb + size) <= threshold_mb:
                    action = "BACKUP_NOW"
                    reason = "High priority scan within capacity allocation"
                    now_count += 1
                    accumulated_mb += size
                elif crit in ["HIGH", "MEDIUM"]:
                    action = "BACKUP_NEXT"
                    reason = "High workload forecasted - queued for next iteration"
                else:
                    action = "DEFER"
                    reason = "Low urgency - deferred to off-peak network window"
                    deferred_count += 1
            else:
                # Normal operational load - process all records
                action = "BACKUP_NOW"
                reason = "Normal system workload - scheduled for immediate backup"
                now_count += 1

            schedule_items.append(
                ScheduleItem(
                    record_id=rec["record_id"],
                    record_type=rec["record_type"],
                    department=rec["department"],
                    criticality=crit,
                    priority_score=rec["priority_score"],
                    data_size_mb=size,
                    action=action,
                    reason=reason
                )
            )

        schedule_resp = ScheduleResponse(
            generated_at=datetime.now(timezone.utc),
            predicted_workload_mb=predicted_mb,
            capacity_threshold_mb=threshold_mb,
            is_capacity_exceeded=is_exceeded,
            total_pending_records=len(pending_records),
            scheduled_now_count=now_count,
            deferred_count=deferred_count,
            schedule=schedule_items
        )

        self._last_schedule = schedule_resp
        logger.info(f"Generated backup schedule with {now_count} IMMEDIATE backups and {deferred_count} DEFERRED items.")
        return schedule_resp

    def get_current_schedule(self) -> ScheduleResponse:
        """Returns the current active backup schedule or generates a new one."""
        if self._last_schedule:
            return self._last_schedule
        return self.generate_schedule()


smart_scheduler = SmartScheduler()
