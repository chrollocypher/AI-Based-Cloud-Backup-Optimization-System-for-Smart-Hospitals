"""Module: src/ml_model/synthetic_ehr/aggregate_hourly_workload.py

Aggregates raw EHR access and backup events into continuous, chronological
1-hour workload windows, keeping access and backup metrics strictly independent.

Hourly Target Schema:
  - window_start_time
  - access_event_count
  - access_volume_mb
  - backup_event_count
  - backup_volume_mb
  - emergency_event_count
"""
import os
import sys
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def aggregate_workload(raw_csv_path: str) -> pd.DataFrame:
    """Aggregates raw access log CSV into continuous 1-hour windows."""
    df = pd.read_csv(raw_csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Floor timestamp to 1-hour window
    df["window_start_time"] = df["timestamp"].dt.floor("1h")

    # Group by hourly window
    windows = []
    min_time = df["window_start_time"].min()
    max_time = df["window_start_time"].max()

    # Generate complete continuous time range (no missing hours)
    all_hours = pd.date_range(start=min_time, end=max_time, freq="1h")

    for hour in all_hours:
        sub = df[df["window_start_time"] == hour]

        # Independent separation between ACCESS and BACKUP
        access_events = sub[sub["access_type"] != "BACKUP"]
        backup_events = sub[sub["access_type"] == "BACKUP"]
        emergency_events = sub[sub["emergency_flag"] == True]

        windows.append({
            "window_start_time": hour.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "access_event_count": int(len(access_events)),
            "access_volume_mb": round(float(access_events["data_size_mb"].sum()), 2),
            "backup_event_count": int(len(backup_events)),
            "backup_volume_mb": round(float(backup_events["data_size_mb"].sum()), 2),
            "emergency_event_count": int(len(emergency_events))
        })

    hourly_df = pd.DataFrame(windows)
    return hourly_df


def main():
    print("=" * 60)
    print("AGGREGATING HOURLY WORKLOAD DATASET")
    print("=" * 60)
    raw_path = os.path.join(PROJECT_ROOT, "dataset/raw/ehr_access_events_raw.csv")
    if not os.path.exists(raw_path):
        from derive_access_logs import main as derive_main
        derive_main()

    hourly_df = aggregate_workload(raw_path)

    proc_dir = os.path.join(PROJECT_ROOT, "dataset/processed")
    os.makedirs(proc_dir, exist_ok=True)
    out_csv = os.path.join(proc_dir, "ehr_hourly_workload_timeseries.csv")

    hourly_df.to_csv(out_csv, index=False)
    print(f"[SUCCESS] Wrote {len(hourly_df)} continuous 1-hour windows to:\n  -> {out_csv}")
    print(f"  Total Access Events: {hourly_df['access_event_count'].sum()}")
    print(f"  Total Access Volume: {hourly_df['access_volume_mb'].sum():.2f} MB")
    print(f"  Total Backup Events: {hourly_df['backup_event_count'].sum()}")
    print(f"  Total Backup Volume: {hourly_df['backup_volume_mb'].sum():.2f} MB")
    print(f"  Total Emergency Events: {hourly_df['emergency_event_count'].sum()}")
    return hourly_df


if __name__ == "__main__":
    main()
