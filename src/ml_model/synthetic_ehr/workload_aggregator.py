"""
EHR Workload Aggregator Module.
Aggregates transformed Synthea EHR event logs into separate hourly and daily workload time series.
Decouples access workload (retrieval volume) from backup workload (data volume to be replicated to cloud).
"""

import os
import pandas as pd
import numpy as np

def aggregate_workload(
    input_events_csv: str,
    output_daily_csv: str,
    output_hourly_csv: str
) -> tuple:
    """
    Reads EHR access logs and computes:
    - Daily aggregated workload (access_workload_mb, backup_workload_mb, emergency_event_count)
    - Hourly aggregated workload (access_workload_mb, backup_workload_mb, emergency_event_count)
    """
    print(f"Aggregating workload from: {input_events_csv}")
    df = pd.read_csv(input_events_csv)
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values('timestamp_dt').reset_index(drop=True)

    # Backup workload: events with backup_status == 'PENDING' (requires cloud storage backup)
    df['backup_volume_mb'] = np.where(df['backup_status'] == 'PENDING', df['data_size_mb'], 0.0)

    # Access workload: all access activity requiring retrieval bandwidth
    df['access_volume_mb'] = df['data_size_mb']

    # Emergency events
    df['emergency_count'] = df['emergency_flag']

    # --- 1. DAILY AGGREGATION ---
    start_date = df['timestamp_dt'].min().floor('D')
    end_date = df['timestamp_dt'].max().ceil('D')
    daily_index = pd.date_range(start=start_date, end=end_date, freq='1D', tz='UTC')

    df_indexed = df.set_index('timestamp_dt')
    daily_agg = df_indexed.resample('1D').agg({
        'backup_volume_mb': 'sum',
        'access_volume_mb': 'sum',
        'emergency_count': 'sum',
        'event_id': 'count'
    }).rename(columns={'event_id': 'total_events'})

    # Reindex to ensure continuous daily time series without missing dates
    daily_full = daily_agg.reindex(daily_index).fillna(0.0).reset_index()
    daily_full = daily_full.rename(columns={'index': 'window_start_time'})
    daily_full['window_start_time'] = daily_full['window_start_time'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    daily_full['backup_workload_mb'] = daily_full['backup_volume_mb'].round(2)
    daily_full['access_workload_mb'] = daily_full['access_volume_mb'].round(2)
    daily_full['emergency_event_count'] = daily_full['emergency_count'].astype(int)
    daily_full['total_event_count'] = daily_full['total_events'].astype(int)

    daily_out = daily_full[[
        'window_start_time',
        'backup_workload_mb',
        'access_workload_mb',
        'emergency_event_count',
        'total_event_count'
    ]]

    os.makedirs(os.path.dirname(output_daily_csv), exist_ok=True)
    daily_out.to_csv(output_daily_csv, index=False)
    print(f"Daily workload series saved to: {output_daily_csv} ({len(daily_out)} days)")

    # --- 2. HOURLY AGGREGATION ---
    hourly_index = pd.date_range(start=start_date, end=end_date, freq='1h', tz='UTC')
    hourly_agg = df_indexed.resample('1h').agg({
        'backup_volume_mb': 'sum',
        'access_volume_mb': 'sum',
        'emergency_count': 'sum',
        'event_id': 'count'
    }).rename(columns={'event_id': 'total_events'})

    hourly_full = hourly_agg.reindex(hourly_index).fillna(0.0).reset_index()
    hourly_full = hourly_full.rename(columns={'index': 'window_start_time'})
    hourly_full['window_start_time'] = hourly_full['window_start_time'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    hourly_full['backup_workload_mb'] = hourly_full['backup_volume_mb'].round(2)
    hourly_full['access_workload_mb'] = hourly_full['access_volume_mb'].round(2)
    hourly_full['emergency_event_count'] = hourly_full['emergency_count'].astype(int)
    hourly_full['total_event_count'] = hourly_full['total_events'].astype(int)

    hourly_out = hourly_full[[
        'window_start_time',
        'backup_workload_mb',
        'access_workload_mb',
        'emergency_event_count',
        'total_event_count'
    ]]

    os.makedirs(os.path.dirname(output_hourly_csv), exist_ok=True)
    hourly_out.to_csv(output_hourly_csv, index=False)
    print(f"Hourly workload series saved to: {output_hourly_csv} ({len(hourly_out)} hours)")

    return daily_out, hourly_out

if __name__ == '__main__':
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    events_in = os.path.join(base_dir, 'dataset', 'synthea', 'processed', 'synthea_ehr_access_logs.csv')
    daily_out_path = os.path.join(base_dir, 'dataset', 'synthea', 'processed', 'synthea_daily_workload.csv')
    hourly_out_path = os.path.join(base_dir, 'dataset', 'synthea', 'processed', 'synthea_hourly_workload.csv')
    aggregate_workload(events_in, daily_out_path, hourly_out_path)
