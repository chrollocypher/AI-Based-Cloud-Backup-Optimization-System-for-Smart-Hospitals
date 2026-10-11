import os
import sys
import numpy as np
import tensorflow as tf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.ml_model.preprocessing.data_loader import load_and_split_data
from src.ml_model.preprocessing.scaler import WorkloadScaler
from src.ml_model.preprocessing.sequence_builder import create_sequences
from src.ml_model.baselines.evaluate_baselines import calculate_metrics

def evaluate_lstm():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    data_path = os.path.join(base_dir, 'dataset', 'processed', 'workload_timeseries_1h.csv')
    model_path = os.path.join(base_dir, 'src', 'ml_model', 'models', 'best_lstm_model.keras')
    
    lookback = 24
    
    # 1. Load data
    train_data, _, test_data, _ = load_and_split_data(data_path, lookback=lookback)
    
    # 2. Scale
    scaler = WorkloadScaler()
    scaler.fit(train_data)
    
    test_scaled = scaler.transform(test_data)
    
    # 3. Create Sequences
    X_test, _ = create_sequences(test_scaled, lookback)
    
    # Raw targets
    _, y_test_raw = create_sequences(test_data, lookback)
    y_true_mb = y_test_raw.flatten()
    
    # 4. Load Model and Predict
    model = tf.keras.models.load_model(model_path)
    preds_scaled = model.predict(X_test, verbose=0)
    
    # Inverse transform
    preds_mb = scaler.inverse_transform(preds_scaled).flatten()
    
    # 5. Evaluate
    mae, rmse, mape, exc = calculate_metrics(y_true_mb, preds_mb)
    
    print(f"LSTM Test Predictions: {len(y_true_mb)}")
    print(f"{'LSTM':<20} | {mae:<10.2f} | {rmse:<10.2f} | {mape:<10.2f} | {exc:<10}")

if __name__ == '__main__':
    evaluate_lstm()
