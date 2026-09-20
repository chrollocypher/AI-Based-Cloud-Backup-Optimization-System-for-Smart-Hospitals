import numpy as np

def create_sequences(data, lookback_window=24):
    """
    Creates time-series sequences (X) and targets (y).
    
    Args:
        data: Numpy array of shape (N, 1)
        lookback_window: Number of past observations to use as input.
        
    Returns:
        X: Numpy array of shape (N - lookback_window, lookback_window, 1)
        y: Numpy array of shape (N - lookback_window, 1)
    """
    X, y = [], []
    for i in range(len(data) - lookback_window):
        X.append(data[i:(i + lookback_window)])
        y.append(data[i + lookback_window])
        
    return np.array(X), np.array(y)
