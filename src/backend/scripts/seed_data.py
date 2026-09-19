"""Seed script to populate sample hospital records for local testing."""
import sys
import os
from datetime import datetime, timedelta, timezone

# Ensure src/backend is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.record import RecordCreate
from app.services.record_service import record_service

SAMPLE_RECORDS = [
    {
        "record_id": "EHR_10025",
        "record_type": "Emergency EHR",
        "department": "Emergency",
        "data_size_mb": 25.4,
        "access_frequency": 18,
    },
    {
        "record_id": "CT_20041",
        "record_type": "CT",
        "department": "Radiology",
        "data_size_mb": 450.0,
        "access_frequency": 12,
    },
    {
        "record_id": "MRI_20231",
        "record_type": "MRI",
        "department": "Neurology",
        "data_size_mb": 780.5,
        "access_frequency": 8,
    },
    {
        "record_id": "MON_30089",
        "record_type": "Monitoring",
        "department": "ICU",
        "data_size_mb": 15.2,
        "access_frequency": 42,
    },
    {
        "record_id": "ADMIN_9812",
        "record_type": "Administrative",
        "department": "Billing",
        "data_size_mb": 5.8,
        "access_frequency": 2,
    },
    {
        "record_id": "SURG_40012",
        "record_type": "Surgical",
        "department": "Operation Theatre",
        "data_size_mb": 310.0,
        "access_frequency": 15,
    }
]


def seed_records():
    print("Seeding sample hospital records...")
    now = datetime.now(timezone.utc)
    for idx, data in enumerate(SAMPLE_RECORDS):

        timestamp = now - timedelta(minutes=idx * 15)
        rec = RecordCreate(
            record_id=data["record_id"],
            record_type=data["record_type"],
            department=data["department"],
            data_size_mb=data["data_size_mb"],
            access_frequency=data["access_frequency"],
            timestamp=timestamp
        )
        created = record_service.create_record(rec)
        print(f" -> Created record {created.record_id} [{created.criticality}] (size: {created.data_size_mb} MB)")

    print("Seeding completed successfully.")


if __name__ == "__main__":
    seed_records()
