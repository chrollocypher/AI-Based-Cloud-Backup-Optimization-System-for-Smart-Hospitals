from datetime import datetime, timezone, timedelta
from app.scheduler.priority_engine import calculate_priority_score, prioritize_records


def test_calculate_priority_score_critical_higher_than_low():
    now = datetime.now(timezone.utc)
    crit_score = calculate_priority_score(
        criticality="CRITICAL",
        created_at=now - timedelta(hours=2),
        access_frequency=20,
        data_size_mb=100.0
    )
    low_score = calculate_priority_score(
        criticality="LOW",
        created_at=now - timedelta(hours=2),
        access_frequency=1,
        data_size_mb=10.0
    )
    assert crit_score > low_score


def test_prioritize_records_sorting():
    now = datetime.now(timezone.utc)
    records = [
        {
            "record_id": "REC_LOW",
            "criticality": "LOW",
            "created_at": now.isoformat(),
            "access_frequency": 1,
            "data_size_mb": 5.0
        },
        {
            "record_id": "REC_CRIT",
            "criticality": "CRITICAL",
            "created_at": now.isoformat(),
            "access_frequency": 25,
            "data_size_mb": 50.0
        }
    ]

    prioritized = prioritize_records(records)
    assert len(prioritized) == 2
    assert prioritized[0]["record_id"] == "REC_CRIT"
    assert prioritized[0]["priority_score"] > prioritized[1]["priority_score"]
