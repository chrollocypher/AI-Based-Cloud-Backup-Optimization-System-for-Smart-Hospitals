"""
Synthea LSTM Model Architecture and Training Module.
Provides training routines for:
1. backup_workload_mb: Predicts daily backup volume requiring cloud backup.
2. access_workload_mb: Predicts daily EHR retrieval/access bandwidth workload.
Trains two separate dedicated LSTM models from scratch with independent scalers and checkpoints.
"""

import os
import sys
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# Ensure package imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.ml_model.synthetic_ehr.data_loader import (
    load_and_split_synthea_workload,
    SyntheaWorkloadScaler,
    create_workload_sequences
)

def build_synthea_lstm(input_shape: tuple) -> tf.keras.Model:
    """
    Builds a robust LSTM architecture with regularized units for Synthea workload forecasting.
    """
    model = Sequential([
        LSTM(48, activation='relu', return_sequences=False, input_shape=input_shape),
        Dropout(0.1),
        Dense(24, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
    return model

def train_synthea_forecaster(
    workload_csv: str,
    target_column: str,
    models_dir: str,
    model_filename: str,
    scaler_filename: str,
    stats_filename: str,
    lookback: int = 14,
    epochs: int = 50,
    batch_size: int = 32
):
    """
    Trains dedicated LSTM for target_column strictly from scratch.
    """
    os.makedirs(models_dir, exist_ok=True)
    model_save_path = os.path.join(models_dir, model_filename)
    scaler_save_path = os.path.join(models_dir, scaler_filename)
    stats_save_path = os.path.join(models_dir, stats_filename)

    print(f"\n=======================================================")
    print(f"Training LSTM for Target: {target_column}")
    print(f"Loading data from: {workload_csv}")
    print(f"=======================================================")

    train_raw, val_raw, test_raw, full_df = load_and_split_synthea_workload(
        workload_csv,
        target_column=target_column,
        lookback=lookback
    )

    # Fit scaler strictly on training split
    scaler = SyntheaWorkloadScaler()
    scaler.fit(train_raw)
    scaler.save(scaler_save_path)
    print(f"Scaler fitted on train (min={scaler.min_:.2f}, max={scaler.max_:.2f}) -> {scaler_save_path}")

    # Scale splits
    train_scaled = scaler.transform(train_raw)
    val_scaled = scaler.transform(val_raw)

    # Build rolling sequences
    X_train, y_train = create_workload_sequences(train_scaled, lookback)
    X_val, y_val = create_workload_sequences(val_scaled, lookback)

    print(f"Train shapes: X={X_train.shape}, y={y_train.shape}")
    print(f"Val shapes:   X={X_val.shape}, y={y_val.shape}")

    model = build_synthea_lstm(input_shape=(lookback, 1))

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=12, restore_best_weights=True),
        ModelCheckpoint(model_save_path, monitor='val_loss', save_best_only=True, verbose=1)
    ]

    print("Beginning LSTM training from scratch...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )

    best_val_loss = min(history.history['val_loss'])
    best_epoch = np.argmin(history.history['val_loss']) + 1

    stats = {
        'target_column': target_column,
        'total_samples': len(full_df),
        'lookback_days': lookback,
        'epochs_trained': len(history.history['loss']),
        'best_epoch': int(best_epoch),
        'best_val_loss': float(best_val_loss),
        'model_parameters': int(model.count_params())
    }
    with open(stats_save_path, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"\nTraining completed for {target_column}!")
    print(f"Best val loss: {best_val_loss:.5f} at epoch {best_epoch}")
    print(f"Model saved to: {model_save_path}")
    return model, scaler, stats

def train_all_models():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    data_csv = os.path.join(base_dir, 'dataset', 'synthea', 'processed', 'synthea_daily_workload.csv')
    out_dir = os.path.join(base_dir, 'src', 'ml_model', 'synthetic_ehr', 'models')

    # 1. Train Backup Workload LSTM
    train_synthea_forecaster(
        workload_csv=data_csv,
        target_column='backup_workload_mb',
        models_dir=out_dir,
        model_filename='best_synthea_backup_lstm.keras',
        scaler_filename='synthea_backup_scaler.json',
        stats_filename='synthea_backup_train_stats.json',
        lookback=14,
        epochs=50
    )

    # 2. Train Access Workload LSTM
    train_synthea_forecaster(
        workload_csv=data_csv,
        target_column='access_workload_mb',
        models_dir=out_dir,
        model_filename='best_synthea_access_lstm.keras',
        scaler_filename='synthea_access_scaler.json',
        stats_filename='synthea_access_train_stats.json',
        lookback=14,
        epochs=50
    )

if __name__ == '__main__':
    train_all_models()
