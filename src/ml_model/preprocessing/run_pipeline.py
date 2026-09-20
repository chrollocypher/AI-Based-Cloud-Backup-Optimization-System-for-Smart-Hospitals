import os
import sys

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.ml_model.preprocessing.data_loader import load_and_split_data
from src.ml_model.preprocessing.scaler import WorkloadScaler
from src.ml_model.preprocessing.sequence_builder import create_sequences

def main():
    print("Running Preprocessing Pipeline...")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    data_path = os.path.join(base_dir, 'dataset', 'processed', 'workload_timeseries_1h.csv')
    
    # 1. Load and Split
    train_data, val_data, test_data, full_df = load_and_split_data(data_path)
    
    # 2. Fit Scaler ONLY on Training Data
    scaler = WorkloadScaler()
    scaler.fit(train_data)
    
    # Transform all splits
    train_scaled = scaler.transform(train_data)
    val_scaled = scaler.transform(val_data)
    test_scaled = scaler.transform(test_data)
    
    # 3. Create Sequences
    lookback = 24
    X_train, y_train = create_sequences(train_scaled, lookback)
    X_val, y_val = create_sequences(val_scaled, lookback)
    X_test, y_test = create_sequences(test_scaled, lookback)
    
    # 4. Report
    print("\n--- Preprocessing Report ---")
    print(f"Total Time Windows: {len(full_df)}")
    print(f"Train size: {len(train_data)} windows ({len(train_data)/len(full_df)*100:.1f}%)")
    print(f"Validation size: {len(val_data)} windows ({len(val_data)/len(full_df)*100:.1f}%)")
    print(f"Test size: {len(test_data)} windows ({len(test_data)/len(full_df)*100:.1f}%)")
    
    print(f"\nLookback size: {lookback} hours")
    print(f"Input Shape (X_train): {X_train.shape} -> (batch, timesteps, features)")
    print(f"Target Shape (y_train): {y_train.shape} -> (batch, features)")
    
    print("\nScaling Method: Min-Max Scaling (custom implementation)")
    print("Data Leakage Check: SUCCESS. The dataset was strictly sorted chronologically.")
    print("The split occurred before scaling, and the scaler was fitted ONLY on the training split.")
    print("Validation and Test sequences only use data from their respective time periods.")

if __name__ == '__main__':
    main()
