from datetime import datetime, timezone
from typing import List, Optional
from app.models.schedule import ScheduleResponse, ScheduleItem
from app.services.record_service import record_service
from app.core.config import settings
from app.core.logging import logger


class SmartScheduler:
    def __init__(self):
        self._last_schedule: Optional[ScheduleResponse] = None

    def generate_schedule(self) -> ScheduleResponse:
        """Generates backup schedule based on ML decision pipeline (LSTM workload forecast, priority scoring, and capacity limits)."""
        from app.services.ml_service import ml_service

        # 1. Fetch pending records
        all_records = [r.model_dump() for r in record_service.list_records()]
        pending_records = [r for r in all_records if r.get("backup_status") == "PENDING"]

        # 2. Execute full ML decision pipeline
        pipeline_res = ml_service.execute_decision_pipeline(pending_records)

        predicted_mb = round(float(pipeline_res["predicted_workload_mb"]), 2)
        threshold_mb = settings.CAPACITY_THRESHOLD_MB
        is_exceeded = predicted_mb > threshold_mb

        scheduled_now = pipeline_res["scheduled_records"]
        deferred = pipeline_res["deferred_records"]

        schedule_items: List[ScheduleItem] = []

        for rec in scheduled_now:
            schedule_items.append(
                ScheduleItem(
                    record_id=rec["record_id"],
                    record_type=rec.get("record_type", "UNKNOWN"),
                    department=rec.get("department", "General"),
                    criticality=rec.get("criticality", "MEDIUM"),
                    priority_score=float(rec.get("priority_score", rec.get("priority", 2.0))),
                    data_size_mb=float(rec.get("data_size_mb", 10.0)),
                    action="BACKUP_NOW",
                    reason="Scheduled for immediate cloud backup by ML decision pipeline"
                )
            )

        deferred_count = 0
        for rec in deferred:
            crit = str(rec.get("criticality", "MEDIUM")).upper()
            next_round = crit in ("CRITICAL", "HIGH")
            if not next_round:
                deferred_count += 1
            schedule_items.append(
                ScheduleItem(
                    record_id=rec["record_id"],
                    record_type=rec.get("record_type", "UNKNOWN"),
                    department=rec.get("department", "General"),
                    criticality=rec.get("criticality", "MEDIUM"),
                    priority_score=float(rec.get("priority_score", rec.get("priority", 1.0))),
                    data_size_mb=float(rec.get("data_size_mb", 10.0)),
                    action="BACKUP_NEXT" if next_round else "DEFER",
                    reason=(
                        "Queued for the next capacity window (high clinical priority)"
                        if next_round
                        else "Deferred to off-peak window by ML capacity scheduler"
                    ),
                )
            )

        schedule_items.sort(key=lambda item: item.priority_score, reverse=True)

        schedule_resp = ScheduleResponse(
            generated_at=datetime.now(timezone.utc),
            predicted_workload_mb=predicted_mb,
            capacity_threshold_mb=threshold_mb,
            is_capacity_exceeded=is_exceeded,
            total_pending_records=len(pending_records),
            scheduled_now_count=len(scheduled_now),
            deferred_count=deferred_count,
            schedule=schedule_items
        )

        self._last_schedule = schedule_resp
        logger.info(
            f"Generated ML backup schedule: {len(scheduled_now)} scheduled, {len(deferred)} deferred "
            f"(Predicted workload: {predicted_mb} MB)"
        )
        return schedule_resp

    def get_current_schedule(self) -> ScheduleResponse:
        """Returns the current active backup schedule or generates a new one."""
        if self._last_schedule:
            return self._last_schedule
        return self.generate_schedule()


smart_scheduler = SmartScheduler()
