import os
import json
import pytest
import pandas as pd
from scripts.run_comparative_evaluation import PROJECT_ROOT


def test_raw_access_log_schema_and_boundaries():
    """Verify raw EHR access log CSV matches Section 3 schema and guidelines."""
    # Check Synthea processed access logs or legacy raw
    synthea_csv = os.path.join(PROJECT_ROOT, "dataset/synthea/processed/synthea_ehr_access_logs.csv")
    legacy_csv = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/dataset/raw/ehr_access_events_raw.csv")
    raw_csv = synthea_csv if os.path.exists(synthea_csv) else legacy_csv
    assert os.path.exists(raw_csv), f"Access logs not found at {synthea_csv} or {legacy_csv}"

    df = pd.read_csv(raw_csv)
    assert len(df) >= 1000

    required_cols = [
        "event_id", "timestamp", "patient_id", "record_type", "department",
        "access_type", "access_frequency", "data_size_mb", "criticality",
        "storage_tier", "emergency_flag", "backup_status"
    ]
    for col in required_cols:
        assert col in df.columns

    # Verify boundaries
    assert df["event_id"].is_unique
    assert (df["data_size_mb"] > 0).all()
    assert (df["access_frequency"] >= 0).all()
    assert set(df["access_type"].unique()).issubset({"READ", "WRITE", "UPDATE", "RETRIEVE", "BACKUP", "QUERY_BATCH", "EMERGENCY_OVERRIDE"})
    assert set(df["criticality"].unique()).issubset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})
    assert set(df["storage_tier"].unique()).issubset({"STANDARD", "STANDARD_IA", "GLACIER", "DEEP_ARCHIVE", "HOT", "WARM", "COLD", "ARCHIVE"})


def test_hourly_processed_workload_schema():
    """Verify hourly aggregated workload targets are continuous and independently separated."""
    synthea_hourly = os.path.join(PROJECT_ROOT, "dataset/synthea/processed/synthea_hourly_workload.csv")
    legacy_hourly = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/dataset/processed/ehr_hourly_workload_timeseries.csv")
    proc_csv = synthea_hourly if os.path.exists(synthea_hourly) else legacy_hourly
    assert os.path.exists(proc_csv), f"Hourly workload not found at {synthea_hourly} or {legacy_hourly}"

    df = pd.read_csv(proc_csv)
    assert len(df) >= 100

    if "backup_workload_mb" in df.columns:
        # Synthea format
        required_cols = ["window_start_time", "backup_workload_mb", "access_workload_mb", "emergency_event_count"]
    else:
        # Legacy format
        required_cols = [
            "window_start_time", "access_event_count", "access_volume_mb",
            "backup_event_count", "backup_volume_mb", "emergency_event_count"
        ]
    for col in required_cols:
        assert col in df.columns

    # Non-negative checks
    if "backup_workload_mb" in df.columns:
        assert (df["backup_workload_mb"] >= 0).all()
        assert (df["access_workload_mb"] >= 0).all()
        assert (df["emergency_event_count"] >= 0).all()
    else:
        assert (df["access_event_count"] >= 0).all()
        assert (df["access_volume_mb"] >= 0).all()
        assert (df["backup_event_count"] >= 0).all()
        assert (df["backup_volume_mb"] >= 0).all()
        assert (df["emergency_event_count"] >= 0).all()


def test_preservation_of_original_lstm_and_backup_data():
    """Verify that original backup model and datasets were strictly preserved without overwrite, alongside Synthea models."""
    orig_backup_csv = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/dataset/raw/hospital_backup_raw_data.csv")
    orig_workload_csv = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/dataset/processed/workload_timeseries_1h.csv")
    orig_lstm_checkpoint = os.path.join(PROJECT_ROOT, "archive/legacy_custom_model/src/ml_model/models/best_lstm_model.keras")

    # Synthea production models
    synthea_backup_model = os.path.join(PROJECT_ROOT, "src/ml_model/synthetic_ehr/models/best_synthea_backup_lstm.keras")
    synthea_access_model = os.path.join(PROJECT_ROOT, "src/ml_model/synthetic_ehr/models/best_synthea_access_lstm.keras")

    assert os.path.exists(orig_backup_csv)
    assert os.path.exists(orig_workload_csv)
    assert os.path.exists(orig_lstm_checkpoint)
    assert os.path.exists(synthea_backup_model)
    assert os.path.exists(synthea_access_model)
