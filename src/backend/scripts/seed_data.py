"""Seed script to populate synthetic hospital EHR records and access events for testing."""
import sys
import os
import uuid
from datetime import datetime, timezone

# Ensure src/backend is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.record import RecordCreate
from app.models.access_log import RawAccessEvent
from app.models.enums import StorageTier, AccessType, Criticality
from app.services.record_service import record_service

SYNTHETIC_RECORDS = [
    {
        "record_id": "EHR_10025",
        "patient_id": "P_SYN_10482",
        "record_type": "Emergency EHR",
        "department": "Emergency",
        "data_size_mb": 25.4,
        "access_frequency": 18,
        "storage_tier": StorageTier.STANDARD,
        "emergency_flag": True
    },
    {
        "record_id": "CT_20041",
        "patient_id": "P_SYN_20391",
        "record_type": "CT",
        "department": "Radiology",
        "data_size_mb": 450.0,
        "access_frequency": 12,
        "storage_tier": StorageTier.STANDARD,
        "emergency_flag": False
    },
    {
        "record_id": "MRI_20231",
        "patient_id": "P_SYN_30912",
        "record_type": "MRI",
        "department": "Neurology",
        "data_size_mb": 780.5,
        "access_frequency": 5,
        "storage_tier": StorageTier.STANDARD_IA,
        "emergency_flag": False
    },
    {
        "record_id": "MON_30089",
        "patient_id": "P_SYN_40129",
        "record_type": "Monitoring",
        "department": "ICU",
        "data_size_mb": 15.2,
        "access_frequency": 42,
        "storage_tier": StorageTier.STANDARD,
        "emergency_flag": True
    },
    {
        "record_id": "ADMIN_9812",
        "patient_id": "P_SYN_50918",
        "record_type": "Administrative",
        "department": "Billing",
        "data_size_mb": 5.8,
        "access_frequency": 0,
        "storage_tier": StorageTier.GLACIER_FLEXIBLE,
        "emergency_flag": False
    },
    {
        "record_id": "SURG_40012",
        "patient_id": "P_SYN_60192",
        "record_type": "Surgical",
        "department": "Operation Theatre",
        "data_size_mb": 310.0,
        "access_frequency": 15,
        "storage_tier": StorageTier.STANDARD,
        "emergency_flag": False
    }
]


def seed_records():
    print("Seeding synthetic hospital EHR records...")
    created = []
    for item in SYNTHETIC_RECORDS:
        rec_in = RecordCreate(**item)
        r = record_service.create_record(rec_in)
        created.append(r)
        print(f"  [+] Ingested record {r.record_id} ({r.department}) -> Tier: {r.storage_tier}")

    # Seed synthetic access events
    print("Seeding sample access events...")
    for rec in created:
        event = RawAccessEvent(
            event_id=f"EVT_{uuid.uuid4().hex[:6].upper()}",
            timestamp=datetime.now(timezone.utc),
            patient_id=rec.patient_id or f"P_SYN_{rec.record_id}",
            record_type=rec.record_type,
            department=rec.department,
            access_type=AccessType.RETRIEVE if rec.emergency_flag else AccessType.READ,
            access_frequency=rec.access_frequency,
            data_size_mb=rec.data_size_mb,
            criticality=Criticality(rec.criticality) if rec.criticality in Criticality.__members__ else Criticality.MEDIUM,
            storage_tier=StorageTier(rec.storage_tier) if rec.storage_tier in StorageTier.__members__ else StorageTier.STANDARD,
            emergency_flag=rec.emergency_flag
        )
        record_service.record_access_event(event)

    print(f"Successfully seeded {len(created)} synthetic hospital records and events.")
    return created


def seed_from_synthea(limit: int = 50):
    """Seeds records and access events directly from Member A Synthea processed access logs."""
    import pandas as pd
    from app.core.config import settings

    csv_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")), settings.SYNTHEA_ACCESS_LOGS_PATH)
    if not os.path.exists(csv_path):
        print(f"Synthea CSV not found at {csv_path}, falling back to synthetic seed.")
        return seed_records()

    print(f"Seeding {limit} records from Synthea dataset ({csv_path})...")
    df = pd.read_csv(csv_path).head(limit)
    created = []

    for _, row in df.iterrows():
        tier_val = str(row.get("storage_tier", "STANDARD")).upper()
        if tier_val in ["HOT", "STANDARD"]:
            st = StorageTier.STANDARD
        elif tier_val in ["WARM", "STANDARD_IA"]:
            st = StorageTier.STANDARD_IA
        elif tier_val in ["COLD", "GLACIER"]:
            st = StorageTier.GLACIER_FLEXIBLE
        else:
            st = StorageTier.GLACIER_DEEP_ARCHIVE

        crit_str = str(row.get("criticality", "MEDIUM")).upper()
        crit = Criticality(crit_str) if crit_str in Criticality.__members__ else Criticality.MEDIUM

        rec_in = RecordCreate(
            record_id=str(row.get("event_id", f"REC_{uuid.uuid4().hex[:6]}")),
            patient_id=str(row.get("patient_id", f"PAT_{uuid.uuid4().hex[:6]}")),
            record_type=str(row.get("record_type", "EHR")),
            department=str(row.get("department", "General")),
            data_size_mb=float(row.get("data_size_mb", 10.0)),
            access_frequency=int(row.get("access_frequency", 1)),
            criticality=crit,
            storage_tier=st,
            emergency_flag=bool(row.get("emergency_flag", False))
        )
        r = record_service.create_record(rec_in)
        created.append(r)

        event = RawAccessEvent(
            event_id=f"EVT_{uuid.uuid4().hex[:6].upper()}",
            timestamp=datetime.now(timezone.utc),
            patient_id=r.patient_id,
            record_type=r.record_type,
            department=r.department,
            access_type=AccessType.RETRIEVE if r.emergency_flag else AccessType.READ,
            access_frequency=r.access_frequency,
            data_size_mb=r.data_size_mb,
            criticality=crit,
            storage_tier=st,
            emergency_flag=r.emergency_flag
        )
        record_service.record_access_event(event)

    print(f"Successfully seeded {len(created)} records from Synthea access logs.")
    return created


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--synthea":
        seed_from_synthea()
    else:
        seed_records()
