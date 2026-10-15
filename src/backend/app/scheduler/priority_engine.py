from datetime import datetime, timezone
from typing import Dict, Any, List
from app.services.record_service import get_criticality_score


def calculate_priority_score(
    criticality: str,
    created_at: datetime,
    access_frequency: int = 1,
    data_size_mb: float = 10.0,
    last_backup: datetime = None
) -> float:
    """Calculates multi-factor urgency priority score for a hospital record.

    Formula:
      Priority Score = (Criticality * 0.4) + (RPO Urgency * 0.3) + (Waiting Time * 0.2) + (Risk Score * 0.1)
    """
    now = datetime.now(timezone.utc)

    # Ensure datetimes are timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    # 1. Criticality Score (1.0 - 4.0)
    crit_score = get_criticality_score(criticality)

    # 2. Waiting Time in hours (normalized to 1.0 - 5.0 scale)
    elapsed_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    waiting_time_score = min(5.0, 1.0 + (elapsed_hours * 0.5))

    # 3. RPO Urgency (1.0 - 5.0 scale based on last backup or age)
    if last_backup:
        if last_backup.tzinfo is None:
            last_backup = last_backup.replace(tzinfo=timezone.utc)
        hours_since_backup = max(0.0, (now - last_backup).total_seconds() / 3600.0)
        rpo_urgency = min(5.0, 1.0 + (hours_since_backup * 0.8))
    else:
        rpo_urgency = min(5.0, 2.0 + (elapsed_hours * 0.6))

    # 4. Risk Score (1.0 - 5.0 scale based on size & access frequency)
    access_factor = min(3.0, access_frequency / 10.0)
    size_factor = min(2.0, data_size_mb / 250.0)
    risk_score = min(5.0, 1.0 + access_factor + size_factor)

    # Combined Priority Formula
    priority_score = (
        (crit_score * 0.4)
        + (rpo_urgency * 0.3)
        + (waiting_time_score * 0.2)
        + (risk_score * 0.1)
    )

    return round(priority_score, 2)


def prioritize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates priority scores and sorts records in descending order of urgency."""
    for record in records:
        created_at = record.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        last_backup = record.get("last_backup")
        if isinstance(last_backup, str):
            last_backup = datetime.fromisoformat(last_backup)

        score = calculate_priority_score(
            criticality=record.get("criticality", "MEDIUM"),
            created_at=created_at or datetime.now(timezone.utc),
            access_frequency=record.get("access_frequency", 1),
            data_size_mb=record.get("data_size_mb", 10.0),
            last_backup=last_backup
        )
        record["priority_score"] = score

    # Sort descending by priority_score
    records.sort(key=lambda x: x["priority_score"], reverse=True)
    return records
