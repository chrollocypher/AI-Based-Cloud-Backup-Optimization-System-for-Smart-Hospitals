import numpy as np

def moving_average_forecast(X_test, window=24):
    """
    Predicts the next hour using the average of the last window hours.
    X_test shape: (samples, lookback_window, 1)
    """
    # Take the last window elements and average them
    return np.mean(X_test[:, -window:, 0], axis=1)
