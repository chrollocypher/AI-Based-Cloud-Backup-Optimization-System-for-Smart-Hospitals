import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.retrieval_service import retrieval_service
from app.services.storage_service import storage_service
from app.services.backup_service import backup_service
from app.services.prediction_service import prediction_service


class MonitoringService:
    """Centralized observability and telemetry service:

    Aggregates all 7 research evaluation metrics, publishes to CloudWatch,
    and evaluates alarm triggers.
    """

    def __init__(self):
        self.namespace = "SmartHospital/EHRStorage"
        self._published_metrics: List[Dict[str, Any]] = []

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Calculates all 7 research metrics declared in the Smart Hospital guide."""
        # 1. Retrieval & Cache Metrics
        retrieval_metrics = retrieval_service.get_metrics()

        # 2. Storage & Cost Metrics
        cost_metrics = storage_service.evaluate_storage_costs()

        # 3. Backup Operations
        jobs = backup_service.list_jobs()
        total_backups = len(jobs)
        completed_backups = len([j for j in jobs if j.status == "COMPLETED"])
        backup_success_rate = round((completed_backups / max(total_backups, 1)) * 100.0, 2) if total_backups > 0 else 100.0

        # 4. Critical Record Availability
        total_emergency = retrieval_metrics.emergency_requests_count
        sla_violations = retrieval_metrics.sla_violations_count
        if total_emergency > 0:
            emergency_within_sla = max(0, total_emergency - sla_violations)
            critical_availability_pct = round((emergency_within_sla / total_emergency) * 100.0, 2)
        else:
            critical_availability_pct = 100.0

        # 5. Dual Forecasting Workload Status
        joint_forecast = prediction_service.get_joint_workload_forecast()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "1_retrieval_latency": {
                    "average_emergency_latency_ms": retrieval_metrics.average_emergency_latency_ms,
                    "by_tier_ms": retrieval_metrics.average_latency_by_tier_ms
                },
                "2_critical_record_availability_percent": critical_availability_pct,
                "3_storage_cost": {
                    "proposed_monthly_usd": cost_metrics.proposed_policy_monthly_cost_usd,
                    "static_standard_baseline_usd": cost_metrics.static_standard_monthly_cost_usd,
                    "projected_monthly_savings_usd": cost_metrics.projected_monthly_savings_usd,
                    "savings_percentage": cost_metrics.savings_percentage
                },
                "4_cache_hit_rate_percent": retrieval_metrics.cache_hit_rate_percent,
                "5_backup_success_rate_percent": backup_success_rate,
                "6_sla_violations": {
                    "count": retrieval_metrics.sla_violations_count,
                    "violation_rate_percent": retrieval_metrics.sla_violation_rate_percent
                },
                "7_prediction_accuracy_baseline": {
                    "backup_volume_forecast_mb": joint_forecast.backup_forecast.predicted_backup_volume_mb,
                    "access_demand_forecast_events": joint_forecast.access_forecast.predicted_access_count,
                    "access_demand_forecast_volume_mb": joint_forecast.access_forecast.predicted_access_volume_mb,
                    "intensity_level": joint_forecast.workload_intensity_level
                }
            }
        }

    def publish_cloudwatch_metrics(self) -> Dict[str, Any]:
        """Publishes custom operational metrics to AWS CloudWatch."""
        telemetry = self.get_system_telemetry()
        m = telemetry["metrics"]

        metric_data = [
            {
                "MetricName": "EmergencyRetrievalLatency",
                "Value": m["1_retrieval_latency"]["average_emergency_latency_ms"],
                "Unit": "Milliseconds",
                "Dimensions": [{"Name": "Service", "Value": "EHRStorage"}]
            },
            {
                "MetricName": "CacheHitRate",
                "Value": m["4_cache_hit_rate_percent"],
                "Unit": "Percent",
                "Dimensions": [{"Name": "Service", "Value": "EHRStorage"}]
            },
            {
                "MetricName": "SLAViolationsCount",
                "Value": m["6_sla_violations"]["count"],
                "Unit": "Count",
                "Dimensions": [{"Name": "Service", "Value": "EHRStorage"}]
            },
            {
                "MetricName": "BackupSuccessRate",
                "Value": m["5_backup_success_rate_percent"],
                "Unit": "Percent",
                "Dimensions": [{"Name": "Service", "Value": "EHRStorage"}]
            },
            {
                "MetricName": "EstimatedMonthlySavingsUSD",
                "Value": m["3_storage_cost"]["projected_monthly_savings_usd"],
                "Unit": "None",
                "Dimensions": [{"Name": "Service", "Value": "EHRStorage"}]
            }
        ]

        if not settings.USE_MOCK_AWS and settings.AWS_ACCESS_KEY_ID:
            try:
                cw = boto3.client("cloudwatch", region_name=settings.AWS_REGION)
                cw.put_metric_data(Namespace=self.namespace, MetricData=metric_data)
                logger.info(f"Published {len(metric_data)} metrics to AWS CloudWatch namespace {self.namespace}")
            except Exception as e:
                logger.warning(f"Failed to publish to CloudWatch ({e}), recording simulated metrics.")

        published_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "namespace": self.namespace,
            "metric_count": len(metric_data),
            "metrics": metric_data,
            "mode": "AWS_LIVE" if (not settings.USE_MOCK_AWS and settings.AWS_ACCESS_KEY_ID) else "SIMULATION"
        }
        self._published_metrics.append(published_entry)
        return published_entry

    def get_alarms_status(self) -> List[Dict[str, Any]]:
        """Evaluates CloudWatch alarms for SLA breaches, backup failures, and peak capacity."""
        telemetry = self.get_system_telemetry()
        m = telemetry["metrics"]

        sla_violations = m["6_sla_violations"]["count"]
        backup_success = m["5_backup_success_rate_percent"]
        intensity = m["7_prediction_accuracy_baseline"]["intensity_level"]

        alarms = [
            {
                "alarm_name": "EHR_Emergency_SLA_Violation_Alarm",
                "metric_name": "SLAViolationsCount",
                "threshold": 0,
                "comparison": "GreaterThanThreshold",
                "current_value": sla_violations,
                "state": "ALARM" if sla_violations > 0 else "OK",
                "severity": "CRITICAL",
                "action": "SNS Email/SMS Alert to On-Call Clinical DevOps"
            },
            {
                "alarm_name": "EHR_Backup_Success_Rate_Alarm",
                "metric_name": "BackupSuccessRate",
                "threshold": 95.0,
                "comparison": "LessThanThreshold",
                "current_value": backup_success,
                "state": "ALARM" if backup_success < 95.0 else "OK",
                "severity": "HIGH",
                "action": "Trigger Step Functions Retry Policy"
            },
            {
                "alarm_name": "EHR_Peak_Capacity_Workload_Alarm",
                "metric_name": "WorkloadIntensityLevel",
                "threshold": "PEAK",
                "comparison": "Equals",
                "current_value": intensity,
                "state": "ALARM" if intensity == "PEAK" else "OK",
                "severity": "MEDIUM",
                "action": "Throttle low-priority backups and prefetch emergency records"
            }
        ]
        return alarms


monitoring_service = MonitoringService()
