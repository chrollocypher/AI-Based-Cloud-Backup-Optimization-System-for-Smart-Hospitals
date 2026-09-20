import os
import sys
import numpy as np

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.ml_model.preprocessing.data_loader import load_and_split_data
from src.ml_model.preprocessing.sequence_builder import create_sequences
from src.ml_model.baselines.naive import naive_forecast
from src.ml_model.baselines.moving_average import moving_average_forecast

def calculate_metrics(y_true, y_pred):
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    
    # Calculate MAPE only where y_true > 1.0 MB
    valid_mask = y_true > 1.0
    excluded_count = len(y_true) - np.sum(valid_mask)
    if np.sum(valid_mask) > 0:
        mape = np.mean(np.abs((y_true[valid_mask] - y_pred[valid_mask]) / y_true[valid_mask])) * 100
    else:
        mape = 0.0
        
    return mae, rmse, mape, excluded_count

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    data_path = os.path.join(base_dir, 'dataset', 'processed', 'workload_timeseries_1h.csv')
    
    lookback = 24
    
    # 1. Load data
    _, _, test_data, _ = load_and_split_data(data_path, lookback=lookback)
    
    # 2. Create Sequences
    X_test, y_test = create_sequences(test_data, lookback)
    
    y_true = y_test.flatten()
    
    # 3. Naive Baseline
    naive_preds = naive_forecast(X_test)
    naive_mae, naive_rmse, naive_mape, naive_exc = calculate_metrics(y_true, naive_preds)
    
    # 4. Moving Average Baseline
    ma_preds = moving_average_forecast(X_test, window=24)
    ma_mae, ma_rmse, ma_mape, ma_exc = calculate_metrics(y_true, ma_preds)
    
    # 5. Report
    print(f"Baselines Test Predictions: {len(y_true)}")
    print(f"{'Naive':<20} | {naive_mae:<10.2f} | {naive_rmse:<10.2f} | {naive_mape:<10.2f} | {naive_exc:<10}")
    print(f"{'Moving Average (24h)':<20} | {ma_mae:<10.2f} | {ma_rmse:<10.2f} | {ma_mape:<10.2f} | {ma_exc:<10}")

if __name__ == '__main__':
    main()
