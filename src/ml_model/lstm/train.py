import os
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.ml_model.preprocessing.data_loader import load_and_split_data
from src.ml_model.preprocessing.scaler import WorkloadScaler
from src.ml_model.preprocessing.sequence_builder import create_sequences
from src.ml_model.lstm.model import build_lstm_model

def train():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    data_path = os.path.join(base_dir, 'dataset', 'processed', 'workload_timeseries_1h.csv')
    model_save_path = os.path.join(base_dir, 'src', 'ml_model', 'models', 'best_lstm_model.keras')
    
    lookback = 24
    
    # 1. Load data
    train_data, val_data, _, _ = load_and_split_data(data_path, lookback=lookback)
    
    # 2. Scale
    scaler = WorkloadScaler()
    scaler.fit(train_data)
    
    train_scaled = scaler.transform(train_data)
    val_scaled = scaler.transform(val_data)
    
    # 3. Create Sequences
    X_train, y_train = create_sequences(train_scaled, lookback)
    X_val, y_val = create_sequences(val_scaled, lookback)
    
    # 4. Build Model
    model = build_lstm_model(input_shape=(lookback, 1))
    
    # 5. Callbacks
    early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    checkpoint = ModelCheckpoint(model_save_path, monitor='val_loss', save_best_only=True)
    
    # 6. Train
    print("Training Model...")
    history = model.fit(
        X_train, y_train,
        epochs=50,
        batch_size=32,
        validation_data=(X_val, y_val),
        callbacks=[early_stopping, checkpoint],
        verbose=1
    )
    
    best_epoch = np.argmin(history.history['val_loss']) + 1
    
    with open('lstm_stats.txt', 'w') as f:
        f.write(f"Parameters: {model.count_params()}\n")
        f.write(f"Epochs trained: {len(history.history['val_loss'])}\n")
        f.write(f"Best validation loss: {history.history['val_loss'][best_epoch-1]:.4f}\n")

if __name__ == '__main__':
    train()
