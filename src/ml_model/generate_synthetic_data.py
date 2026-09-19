import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta
import os

# 1. Configuration & Constants
SEED = 42
np.random.seed(SEED)

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 1, 1)
TOTAL_HOURS = int((END_DATE - START_DATE).total_seconds() / 3600)

# Criticality Map
CRITICALITY = {
    'CRITICAL': 4,
    'HIGH': 3,
    'MEDIUM': 2,
    'LOW': 1
}

# Departments configuration
DEPARTMENTS = {
    'RAD': {'types': ['DICOM'], 'size_mean': 300, 'size_std': 100, 'criticality': CRITICALITY['HIGH'], 'freq_weight': 0.15},
    'CARD': {'types': ['ECG', 'DICOM'], 'size_mean': 50, 'size_std': 20, 'criticality': CRITICALITY['HIGH'], 'freq_weight': 0.15},
    'ER': {'types': ['EHR', 'IoT'], 'size_mean': 2, 'size_std': 1, 'criticality': CRITICALITY['CRITICAL'], 'freq_weight': 0.30},
    'LAB': {'types': ['LAB_RESULT'], 'size_mean': 5, 'size_std': 2, 'criticality': CRITICALITY['HIGH'], 'freq_weight': 0.20},
    'ADMIN': {'types': ['EHR', 'BILLING'], 'size_mean': 1, 'size_std': 0.5, 'criticality': CRITICALITY['LOW'], 'freq_weight': 0.20},
}

# 2. Base Workload Profile Generation
def generate_hourly_workload_factors(total_hours, start_date):
    """
    Generates a multiplier for expected file counts per hour based on daily/weekly cycles.
    """
    hours = np.arange(total_hours)
    timestamps = [start_date + timedelta(hours=int(h)) for h in hours]
    
    factors = []
    for t in timestamps:
        # Daily cycle: peak around 08-18, drop at night
        hour = t.hour
        if 8 <= hour <= 18:
            daily_factor = np.random.normal(1.0, 0.1)
        else:
            daily_factor = np.random.normal(0.2, 0.05)
            
        # Weekly cycle: lower on weekends
        weekday = t.weekday()
        if weekday >= 5: # Saturday, Sunday
            weekly_factor = 0.5
        else:
            weekly_factor = 1.0
            
        factors.append(max(0.01, daily_factor * weekly_factor))
        
    return np.array(factors), timestamps

# 3. Emergency Spikes Injection
def inject_emergency_spikes(factors, timestamps, num_spikes=10):
    """
    Injects random high-volume spikes into the factors array.
    """
    spike_indices = np.random.choice(len(factors), size=num_spikes, replace=False)
    for idx in spike_indices:
        duration = np.random.randint(4, 12) # 4 to 12 hours
        multiplier = np.random.uniform(3.0, 6.0)
        
        for i in range(duration):
            if idx + i < len(factors):
                factors[idx + i] *= multiplier
                
    return factors, num_spikes

# 4. Generate Raw Records
def generate_raw_records(factors, timestamps):
    records = []
    
    # Tuning to reach ~300,000 - 400,000 records
    base_files_per_hour = 60 
    
    dept_names = list(DEPARTMENTS.keys())
    dept_weights = [DEPARTMENTS[d]['freq_weight'] for d in dept_names]
    
    for idx, t in enumerate(timestamps):
        num_files = int(base_files_per_hour * factors[idx])
        
        if num_files <= 0:
            continue
            
        # Generate timestamps for these files randomly within the hour
        minutes = np.random.randint(0, 60, size=num_files)
        seconds = np.random.randint(0, 60, size=num_files)
        
        # Sample departments
        chosen_depts = np.random.choice(dept_names, size=num_files, p=dept_weights)
        
        for i in range(num_files):
            dept = chosen_depts[i]
            dept_config = DEPARTMENTS[dept]
            
            record_time = t + timedelta(minutes=int(minutes[i]), seconds=int(seconds[i]))
            
            data_type = np.random.choice(dept_config['types'])
            
            # File size logic
            size = np.random.normal(dept_config['size_mean'], dept_config['size_std'])
            size = max(0.01, size) # ensure positive size
            
            crit = dept_config['criticality']
            
            records.append({
                'record_id': str(uuid.uuid4()),
                'timestamp': record_time.strftime('%Y-%m-%dT%H:%M:%SZ'), # UTC ISO
                'department': dept,
                'data_type': data_type,
                'file_size_mb': round(size, 2),
                'criticality': crit
            })
            
    return pd.DataFrame(records)

# 5. Process and Aggregate
def process_data(df, start_date, end_date):
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    
    # Full range of hourly windows
    full_range = pd.date_range(start=start_date, end=end_date, freq='1h', inclusive='left', tz='UTC')
    
    df_indexed = df.set_index('timestamp_dt')
    # Resample and sum sizes
    agg_df = df_indexed.resample('1h').agg({'file_size_mb': 'sum'}).reset_index()
    
    # Merge with full range to ensure no missing windows
    full_df = pd.DataFrame({'window_start_time': full_range})
    merged_df = pd.merge(full_df, agg_df, left_on='window_start_time', right_on='timestamp_dt', how='left')
    
    merged_df['total_volume_mb'] = merged_df['file_size_mb'].fillna(0.0).round(2)
    
    processed_df = merged_df[['window_start_time', 'total_volume_mb']].copy()
    processed_df['window_start_time'] = processed_df['window_start_time'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return processed_df

def main():
    print("Starting Synthetic Dataset Generation...")
    
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    raw_path = os.path.join(base_dir, 'dataset', 'raw', 'hospital_backup_raw_data.csv')
    processed_path = os.path.join(base_dir, 'dataset', 'processed', 'workload_timeseries_1h.csv')
    
    os.makedirs(os.path.dirname(raw_path), exist_ok=True)
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    
    # Generate workload factors
    factors, timestamps = generate_hourly_workload_factors(TOTAL_HOURS, START_DATE)
    
    # Inject spikes
    num_spikes = 15
    factors, num_spikes = inject_emergency_spikes(factors, timestamps, num_spikes=num_spikes)
    
    # Generate Raw
    print("Generating raw records...")
    raw_df = generate_raw_records(factors, timestamps)
    
    # Process
    print("Aggregating into 1-hour windows...")
    processed_df = process_data(raw_df, START_DATE, END_DATE)
    
    # Save
    raw_df.drop('timestamp_dt', axis=1, errors='ignore').to_csv(raw_path, index=False)
    processed_df.to_csv(processed_path, index=False)
    
    # Summary
    print("\n--- Generation Summary ---")
    print(f"Total Raw Records: {len(raw_df)}")
    print(f"Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    print(f"Departments: {list(DEPARTMENTS.keys())}")
    
    types = set()
    for d in DEPARTMENTS.values():
        types.update(d['types'])
    print(f"Data Types: {list(types)}")
    
    print(f"Total Data Volume: {raw_df['file_size_mb'].sum():.2f} MB")
    print(f"Min Hourly Workload: {processed_df['total_volume_mb'].min():.2f} MB")
    print(f"Max Hourly Workload: {processed_df['total_volume_mb'].max():.2f} MB")
    print(f"Mean Hourly Workload: {processed_df['total_volume_mb'].mean():.2f} MB")
    print(f"Number of Emergency Spike Periods: {num_spikes}")
    
    print("\nFiles successfully created:")
    print(f"- {raw_path}")
    print(f"- {processed_path}")

if __name__ == "__main__":
    main()
