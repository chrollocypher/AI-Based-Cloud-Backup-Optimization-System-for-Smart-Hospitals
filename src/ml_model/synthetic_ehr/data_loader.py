"""
Data Loader and Scaler for Synthea-based Workload Forecasting.
Enforces strict chronological train/validation/test split (70% train, 15% val, 15% test).
Fits MinMax scaler ONLY on the training split to prevent any data leakage.
"""

import json
import numpy as np
import pandas as pd

class SyntheaWorkloadScaler:
    """
    Min-Max Scaler fitted strictly on training data.
    Provides serialization to/from JSON.
    """
    def __init__(self):
        self.min_ = None
        self.max_ = None
        self.scale_ = None

    def fit(self, data: np.ndarray):
        """Fits scaler strictly on provided training array."""
        self.min_ = float(np.min(data))
        self.max_ = float(np.max(data))
        self.scale_ = self.max_ - self.min_
        if self.scale_ == 0.0:
            self.scale_ = 1.0
        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        if self.min_ is None or self.scale_ is None:
            raise ValueError("Scaler has not been fitted.")
        return (data - self.min_) / self.scale_

    def inverse_transform(self, data: np.ndarray) -> np.ndarray:
        if self.min_ is None or self.scale_ is None:
            raise ValueError("Scaler has not been fitted.")
        return (data * self.scale_) + self.min_

    def save(self, filepath: str):
        params = {'min': self.min_, 'max': self.max_, 'scale': self.scale_}
        with open(filepath, 'w') as f:
            json.dump(params, f, indent=2)

    def load(self, filepath: str):
        with open(filepath, 'r') as f:
            params = json.load(f)
        self.min_ = params['min']
        self.max_ = params['max']
        self.scale_ = params['scale']
        return self

def load_and_split_synthea_workload(
    filepath: str,
    target_column: str = 'backup_workload_mb',
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    lookback: int = 14
):
    """
    Loads Synthea workload time series, sorts chronologically, and partitions into train, val, test.
    Returns raw splits and full dataframe.
    """
    df = pd.read_csv(filepath)
    df['window_start_time'] = pd.to_datetime(df['window_start_time'])
    df = df.sort_values('window_start_time').reset_index(drop=True)

    values = df[target_column].values.astype(np.float32).reshape(-1, 1)
    n = len(values)

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_data = values[:train_end]
    val_data = values[train_end - lookback : val_end]
    test_data = values[val_end - lookback :]

    return train_data, val_data, test_data, df

def create_workload_sequences(data: np.ndarray, lookback: int = 14):
    """
    Generates rolling sequences for LSTM training.
    X: shape (N - lookback, lookback, 1)
    y: shape (N - lookback, 1)
    """
    X, y = [], []
    for i in range(len(data) - lookback):
        X.append(data[i : i + lookback])
        y.append(data[i + lookback])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)
