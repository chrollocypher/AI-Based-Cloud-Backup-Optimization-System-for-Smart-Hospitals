def naive_forecast(X_test):
    """
    Predicts the next hour using the very last hour of the lookback sequence.
    X_test shape: (samples, lookback_window, 1)
    """
    # The last element in the sequence is the most recent observation
    return X_test[:, -1, 0]
