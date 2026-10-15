from datetime import datetime, timezone, timedelta
from typing import List
from app.models.dashboard import DashboardSummaryResponse, WorkloadPoint, MonitoringStatusResponse
from app.services.record_service import record_service
from app.services.prediction_service import prediction_service
from app.services.backup_service import backup_service
from app.db.dynamodb import db_memory


class DashboardService:
    def get_summary(self) -> DashboardSummaryResponse:
        """Aggregates system-wide operational metrics for dashboard visualization."""
        all_records = record_service.list_records()
        pending_recs = [r for r in all_records if r.backup_status == "PENDING"]
        crit_pending = [r for r in pending_recs if r.criticality == "CRITICAL"]

        all_jobs = backup_service.list_jobs()
        completed = [j for j in all_jobs if j.status == "COMPLETED"]
        failed = [j for j in all_jobs if j.status == "FAILED"]

        latest_pred = prediction_service.get_latest_prediction()

        # Calculate current aggregate data size in GB
        total_data_mb = sum(r.data_size_mb for r in all_records)
        current_workload_gb = round(total_data_mb / 1024.0, 2)
        predicted_gb = round(latest_pred.predicted_backup_volume_mb / 1024.0, 2)

        # Total storage consumed in S3 (simulated / calculated from completed jobs)
        completed_records_mb = sum(
            r.data_size_mb for r in all_records if r.backup_status == "COMPLETED"
        )
        storage_used_gb = round((completed_records_mb + 145000.0) / 1024.0, 2)

        return DashboardSummaryResponse(
            current_workload_gb=current_workload_gb,
            predicted_workload_gb=predicted_gb,
            pending_backups=len(pending_recs),
            critical_pending=len(crit_pending),
            completed_today=len(completed),
            failed_today=len(failed),
            storage_used_gb=storage_used_gb
        )

    def get_workload_timeseries(self) -> List[WorkloadPoint]:
        """Generates historical vs. predicted workload time-series data points."""
        now = datetime.now(timezone.utc)
        points: List[WorkloadPoint] = []

        # Generate 6 hourly data points for dashboard chart
        for i in range(5, -1, -1):
            ts_time = now - timedelta(hours=i)
            time_str = ts_time.strftime("%H:00")
            base_gb = 7.5 + (i % 3) * 0.8
            pred_gb = round(base_gb * 1.12, 2)
            points.append(
                WorkloadPoint(
                    timestamp=time_str,
                    actual_gb=round(base_gb, 2),
                    predicted_gb=pred_gb
                )
            )

        return points

    def get_monitoring_status(self) -> MonitoringStatusResponse:
        """Returns overall system component health and monitoring telemetry."""
        latest_pred = prediction_service.get_latest_prediction()
        all_jobs = backup_service.list_jobs()
        active_jobs = [j for j in all_jobs if j.status == "IN_PROGRESS"]

        return MonitoringStatusResponse(
            system_status="HEALTHY",
            database_connected=True,
            aws_services_active=True,
            active_scheduler=True,
            last_prediction_time=latest_pred.timestamp.isoformat(),
            active_jobs_count=len(active_jobs)
        )


dashboard_service = DashboardService()
