import pandas as pd
import numpy as np

raw_path = 'dataset/raw/hospital_backup_raw_data.csv'
proc_path = 'dataset/processed/workload_timeseries_1h.csv'

raw_df = pd.read_csv(raw_path)
proc_df = pd.read_csv(proc_path)

proc_df['window_start_time'] = pd.to_datetime(proc_df['window_start_time'])
raw_df['timestamp'] = pd.to_datetime(raw_df['timestamp'])

print('--- Data Quality ---')
print(f"Missing Values (Raw): {raw_df.isnull().sum().to_dict()}")
print(f"Missing Values (Proc): {proc_df.isnull().sum().to_dict()}")
print(f"Duplicate Records (Raw): {raw_df.duplicated().sum()}")
print(f"Duplicate Records (Proc): {proc_df.duplicated().sum()}")

print('--- Time-Series Continuity ---')
time_diff = proc_df['window_start_time'].diff().dropna()
print(f"Consistent 1h gaps: {all(time_diff == pd.Timedelta(hours=1))}")
print(f"Number of hourly windows: {len(proc_df)}")
print(f"Zero-workload windows: {(proc_df['total_volume_mb'] == 0).sum()}")

print('--- Hourly Workload Stats ---')
print(proc_df['total_volume_mb'].describe().to_dict())

print('--- Daily & Weekly Patterns ---')
proc_df['hour'] = proc_df['window_start_time'].dt.hour
proc_df['weekday'] = proc_df['window_start_time'].dt.weekday
proc_df['is_weekend'] = proc_df['weekday'] >= 5

print(f"Mean workload (Day 8-18): {proc_df[(proc_df['hour'] >= 8) & (proc_df['hour'] <= 18)]['total_volume_mb'].mean():.2f}")
print(f"Mean workload (Night): {proc_df[(proc_df['hour'] < 8) | (proc_df['hour'] > 18)]['total_volume_mb'].mean():.2f}")
print(f"Mean workload (Weekday): {proc_df[~proc_df['is_weekend']]['total_volume_mb'].mean():.2f}")
print(f"Mean workload (Weekend): {proc_df[proc_df['is_weekend']]['total_volume_mb'].mean():.2f}")

print('--- Spikes ---')
mean_vol = proc_df['total_volume_mb'].mean()
std_vol = proc_df['total_volume_mb'].std()
spikes = proc_df[proc_df['total_volume_mb'] > mean_vol + 3*std_vol]
print(f"Number of spikes (> 3 std): {len(spikes)}")
if len(spikes) > 0:
    print(f"Spike Magnitudes (Top 5): {sorted(spikes['total_volume_mb'].values, reverse=True)[:5]}")

print('--- Department Stats ---')
dept_stats = raw_df.groupby('department')['file_size_mb'].agg(['count', 'sum'])
print(dept_stats.to_dict())

print('--- Data Type Stats ---')
type_stats = raw_df.groupby('data_type')['file_size_mb'].agg(['count', 'sum'])
print(type_stats.to_dict())
