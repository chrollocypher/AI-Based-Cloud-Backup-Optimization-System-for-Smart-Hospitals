import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.models.backup import BackupJobResponse, BackupJobCreate
from app.services.record_service import record_service
from app.services.aws_service import aws_service
from app.scheduler.scheduler import smart_scheduler
from app.db.dynamodb import db_memory
from app.core.logging import logger


class BackupService:
    def trigger_backup(self, payload: Optional[BackupJobCreate] = None) -> List[BackupJobResponse]:
        """Triggers backup workflow execution for a single record or active schedule."""
        jobs: List[BackupJobResponse] = []

        if payload and payload.record_id:
            record = record_service.get_record(payload.record_id)
            if not record:
                raise ValueError(f"Record with ID '{payload.record_id}' not found.")
            target_records = [record]
        else:
            # Trigger for all BACKUP_NOW items in active schedule
            schedule = smart_scheduler.generate_schedule()
            backup_now_ids = [item.record_id for item in schedule.schedule if item.action == "BACKUP_NOW"]
            target_records = [record_service.get_record(rid) for rid in backup_now_ids if record_service.get_record(rid)]

        now = datetime.now(timezone.utc)

        for rec in target_records:
            job_id = f"JOB_{uuid.uuid4().hex[:8].upper()}"
            s3_path = aws_service.get_s3_destination(rec.record_id, rec.record_type)

            exec_info = aws_service.trigger_step_function(
                record_id=rec.record_id,
                priority_score=rec.priority_score
            )

            job_dict = {
                "job_id": job_id,
                "record_id": rec.record_id,
                "scheduled_at": now.isoformat(),
                "started_at": now.isoformat(),
                "completed_at": now.isoformat(),  # Simulated quick execution in local mode
                "status": "COMPLETED",
                "s3_location": s3_path,
                "error_message": None,
                "execution_arn": exec_info.get("executionArn")
            }

            db_memory.put_job(job_dict)

            # Update record backup_status & last_backup timestamp in DB
            rec_dict = db_memory.get_record(rec.record_id)
            if rec_dict:
                rec_dict["backup_status"] = "COMPLETED"
                rec_dict["last_backup"] = now.isoformat()
                db_memory.put_record(rec_dict)

            jobs.append(BackupJobResponse(**job_dict))
            logger.info(f"Triggered backup job {job_id} for record {rec.record_id} -> {s3_path}")

        return jobs

    def list_jobs(self, status_filter: Optional[str] = None) -> List[BackupJobResponse]:
        """Lists backup execution jobs, optionally filtered by status."""
        raw_jobs = db_memory.list_jobs(status_filter=status_filter)
        return [BackupJobResponse(**j) for j in raw_jobs]

    def get_job(self, job_id: str) -> Optional[BackupJobResponse]:
        """Retrieves details of a specific backup job."""
        job_data = db_memory.get_job(job_id)
        if not job_data:
            return None
        return BackupJobResponse(**job_data)

    def retry_job(self, job_id: str) -> BackupJobResponse:
        """Retries a failed or stalled backup job."""
        job_data = db_memory.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job with ID '{job_id}' not found.")

        rec_id = job_data["record_id"]
        rec = record_service.get_record(rec_id)
        if not rec:
            raise ValueError(f"Record with ID '{rec_id}' no longer exists.")

        now = datetime.now(timezone.utc)
        exec_info = aws_service.trigger_step_function(
            record_id=rec.record_id,
            priority_score=rec.priority_score
        )

        job_data.update({
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "status": "COMPLETED",
            "error_message": None,
            "execution_arn": exec_info.get("executionArn")
        })

        db_memory.put_job(job_data)

        rec_dict = db_memory.get_record(rec_id)
        if rec_dict:
            rec_dict["backup_status"] = "COMPLETED"
            rec_dict["last_backup"] = now.isoformat()
            db_memory.put_record(rec_dict)

        logger.info(f"Successfully retried backup job {job_id}")
        return BackupJobResponse(**job_data)


backup_service = BackupService()
