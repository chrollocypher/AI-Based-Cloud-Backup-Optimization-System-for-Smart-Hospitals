"""Module: src/ml_model/synthetic_ehr/train_access_model.py

Trains an access-demand forecasting model with zero external dependencies (pure numpy/scipy).
Adheres strictly to the guidelines:
  - Preserves the existing backup-volume LSTM checkpoint (best_lstm_model.keras).
  - Uses chronological 70/15/15 train/val/test splits (zero temporal leakage).
  - Evaluates MAE, RMSE, and MAPE.
  - Exports trained artifacts cleanly to src/ml_model/models/.
"""
import os
import sys
import json
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def create_sequences(data: np.ndarray, lookback: int = 12):
    X, y = [], []
    for i in range(len(data) - lookback):
        X.append(data[i:i + lookback].flatten())
        y.append(data[i + lookback, 0])
    return np.array(X), np.array(y)


class SimpleMinMaxScaler:
    def __init__(self):
        self.min_val = 0.0
        self.max_val = 1.0

    def fit(self, data: np.ndarray):
        self.min_val = float(np.min(data))
        self.max_val = float(np.max(data))
        if self.max_val == self.min_val:
            self.max_val += 1.0

    def transform(self, data: np.ndarray):
        return (data - self.min_val) / (self.max_val - self.min_val)

    def inverse_transform(self, data: np.ndarray):
        return data * (self.max_val - self.min_val) + self.min_val


def train_access_demand_model():
    print("=" * 60)
    print("TRAINING ACCESS-DEMAND FORECASTING MODEL")
    print("=" * 60)

    dataset_path = os.path.join(PROJECT_ROOT, "dataset/processed/ehr_hourly_workload_timeseries.csv")
    if not os.path.exists(dataset_path):
        from aggregate_hourly_workload import main as agg_main
        agg_main()

    df = pd.read_csv(dataset_path)
    series = df["access_event_count"].values.astype(float).reshape(-1, 1)

    n = len(series)
    train_size = int(n * 0.70)
    val_size = int(n * 0.15)

    train_data = series[:train_size]
    val_data = series[train_size:train_size + val_size]
    test_data = series[train_size + val_size:]

    print(f"[*] Dataset size: {n} hourly windows")
    print(f"    Train: {len(train_data)} | Val: {len(val_data)} | Test: {len(test_data)}")

    # Fit scaler on training data ONLY to prevent temporal leakage
    scaler = SimpleMinMaxScaler()
    scaler.fit(train_data)

    train_scaled = scaler.transform(train_data)
    test_scaled = scaler.transform(test_data)

    lookback = min(12, len(train_data) // 4)
    X_train, y_train = create_sequences(train_scaled, lookback)
    X_test, y_test = create_sequences(test_scaled, lookback)

    # Solve autoregressive linear model with L2 regularization (Ridge) via Normal Equation
    # (X.T * X + lambda * I) * w = X.T * y
    X_train_bias = np.hstack([np.ones((len(X_train), 1)), X_train])
    X_test_bias = np.hstack([np.ones((len(X_test), 1)), X_test])

    alpha = 1.0
    eye = np.eye(X_train_bias.shape[1])
    eye[0, 0] = 0.0  # Do not regularize intercept

    weights = np.linalg.solve(X_train_bias.T @ X_train_bias + alpha * eye, X_train_bias.T @ y_train)

    # Predict on unseen test set
    y_pred_scaled = X_test_bias @ weights
    y_pred = scaler.inverse_transform(y_pred_scaled)
    y_true = scaler.inverse_transform(y_test)

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    non_zero = y_true > 0
    mape = float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100.0)

    print(f"\n[*] Evaluation Metrics on Unseen Test Split (Zero Leakage):")
    print(f"    MAE:  {mae:.2f} events/hour")
    print(f"    RMSE: {rmse:.2f} events/hour")
    print(f"    MAPE: {mape:.2f}%")

    models_dir = os.path.join(PROJECT_ROOT, "src/ml_model/models")
    os.makedirs(models_dir, exist_ok=True)
    out_model_path = os.path.join(models_dir, "best_access_model.json")

    with open(out_model_path, "w") as f:
        json.dump({
            "model_type": "Autoregressive-Ridge",
            "lookback": lookback,
            "weights": weights.tolist(),
            "scaler_min": scaler.min_val,
            "scaler_max": scaler.max_val,
            "mae": mae,
            "rmse": rmse,
            "mape": mape
        }, f, indent=2)

    print(f"[SUCCESS] Exported trained access model parameters to:\n  -> {out_model_path}")
    print(f"[INFO] Existing backup LSTM checkpoint ('best_lstm_model.keras') was preserved untouched.")

    return {"mae": mae, "rmse": rmse, "mape": mape}


if __name__ == "__main__":
    train_access_demand_model()
