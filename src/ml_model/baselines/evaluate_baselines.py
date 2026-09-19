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
    
    # 1. Load data
    _, _, test_data, _ = load_and_split_data(data_path)
    
    # Note: The prompt specifies "Use the original workload values in MB for evaluation, not scaled values."
    # We will NOT use the scaler here, just raw values.
    
    # 2. Create Sequences
    lookback = 24
    X_test, y_test = create_sequences(test_data, lookback)
    
    # Flatten y_test for easier metric calculation
    y_true = y_test.flatten()
    
    # 3. Naive Baseline
    naive_preds = naive_forecast(X_test)
    naive_mae, naive_rmse, naive_mape, naive_exc = calculate_metrics(y_true, naive_preds)
    
    # 4. Moving Average Baseline
    ma_preds = moving_average_forecast(X_test, window=24)
    ma_mae, ma_rmse, ma_mape, ma_exc = calculate_metrics(y_true, ma_preds)
    
    # 5. Report
    print("Baseline Evaluation Results (Test Set, Original MB values)")
    print("-" * 75)
    print(f"{'Model':<20} | {'MAE (MB)':<10} | {'RMSE (MB)':<10} | {'MAPE (%)':<10} | {'Excluded':<10}")
    print("-" * 75)
    print(f"{'Naive':<20} | {naive_mae:<10.2f} | {naive_rmse:<10.2f} | {naive_mape:<10.2f} | {naive_exc:<10}")
    print(f"{'Moving Average (24h)':<20} | {ma_mae:<10.2f} | {ma_rmse:<10.2f} | {ma_mape:<10.2f} | {ma_exc:<10}")
    print("-" * 75)

if __name__ == '__main__':
    main()
