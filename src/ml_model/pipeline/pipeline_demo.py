"""
Executable demonstration of the AI decision pipeline.
"""
import os
import pandas as pd
import numpy as np

# Suppress TensorFlow logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

from src.ml_model.preprocessing.scaler import WorkloadScaler
from src.ml_model.pipeline.decision_pipeline import run_pipeline

def run_demo():
    print("AI Backup Decision Pipeline")
    print("===========================\n")
    
    # 1. Load the processed workload time series
    dataset_path = "dataset/processed/workload_timeseries_1h.csv"
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return
        
    df = pd.read_csv(dataset_path)
    workload_data = df['total_volume_mb'].values.reshape(-1, 1)
    
    # 2. Fit the scaler ONLY on the training portion (70%)
    train_size = int(len(workload_data) * 0.7)
    train_data = workload_data[:train_size]
    
    scaler = WorkloadScaler()
    scaler.fit(train_data)
    
    # 3. Extract the most recent 24 historical workload values from training set
    historical_workload = train_data[-24:].flatten()
    
    # 4. Load the trained LSTM model
    model_path = "src/ml_model/models/best_lstm_model.keras"
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        return
        
    lstm_model = tf.keras.models.load_model(model_path)
    
    # 5 & 6. Create sample backup records
    sample_records = [
        {"record_id": "bck_001", "department": "ICU", "criticality": "CRITICAL", "data_size_mb": 850.0},
        {"record_id": "bck_002", "department": "General", "criticality": "LOW", "data_size_mb": 1200.0},
        {"record_id": "bck_003", "department": "Cardiology", "criticality": "HIGH", "data_size_mb": 450.0},
        {"record_id": "bck_004", "department": "Admin", "criticality": "MEDIUM", "data_size_mb": 200.0},
        {"record_id": "bck_005", "department": "ER", "criticality": "CRITICAL", "data_size_mb": 600.0},
    ]
    
    # Run the pipeline
    result = run_pipeline(lstm_model, scaler, historical_workload, sample_records)
    
    # 9. Print the complete decision flow
    print("Predicted Next-Hour Workload:")
    print(f"{result.predicted_workload_mb:.2f} MB\n")
    
    print("Backup Priority Assignment:")
    print("-" * 32)
    print(f"{'ID':<10}{'Criticality':<15}{'Priority':<12}{'Size'}")
    
    all_processed = result.scheduled_records + result.deferred_records
    all_processed.sort(key=lambda x: (-x['priority'], x['record_id']))
    
    for rec in all_processed:
        print(f"{rec['record_id']:<10}{rec['criticality']:<15}{rec['priority']:<12}{rec['data_size_mb']:.1f} MB")
        
    print("\nScheduling Result:")
    print("-" * 32)
    print("Scheduled:")
    for rec in result.scheduled_records:
        print(f"  - [{rec['priority']}] {rec['record_id']} ({rec['data_size_mb']:.1f} MB)")
        
    if not result.scheduled_records:
        print("  (None)")
        
    print("\nDeferred:")
    for rec in result.deferred_records:
        print(f"  - [{rec['priority']}] {rec['record_id']} ({rec['data_size_mb']:.1f} MB)")
        
    if not result.deferred_records:
        print("  (None)")
        
    print(f"\nTotal Scheduled Volume: {result.total_scheduled_volume_mb:.2f} MB")
    print(f"Remaining Capacity: {result.remaining_capacity_mb:.2f} MB")

if __name__ == "__main__":
    run_demo()
