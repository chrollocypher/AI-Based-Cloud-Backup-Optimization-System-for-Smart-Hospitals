import pandas as pd
import numpy as np

def load_and_split_data(filepath, train_ratio=0.7, val_ratio=0.15, lookback=24):
    """
    Loads data, sorts chronologically, and splits into train/val/test.
    """
    df = pd.read_csv(filepath)
    df['window_start_time'] = pd.to_datetime(df['window_start_time'])
    df = df.sort_values('window_start_time').reset_index(drop=True)
    
    # Extract the target series
    values = df['total_volume_mb'].values.reshape(-1, 1)
    
    n = len(values)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_data = values[:train_end]
    val_data = values[train_end - lookback : val_end]
    test_data = values[val_end - lookback :]
    
    return train_data, val_data, test_data, df
