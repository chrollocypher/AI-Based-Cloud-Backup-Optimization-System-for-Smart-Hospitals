import numpy as np

class WorkloadScaler:
    """
    A simple Min-Max Scaler to scale features between 0 and 1.
    """
    def __init__(self):
        self.min_ = None
        self.max_ = None
        self.scale_ = None
        
    def fit(self, data):
        """Fits the scaler ONLY on the provided data (should be train data)."""
        self.min_ = np.min(data, axis=0)
        self.max_ = np.max(data, axis=0)
        self.scale_ = self.max_ - self.min_
        # Avoid division by zero
        self.scale_[self.scale_ == 0] = 1.0
        return self
        
    def transform(self, data):
        """Transforms data using the fitted parameters."""
        if self.min_ is None or self.max_ is None:
            raise ValueError("Scaler has not been fitted yet.")
        return (data - self.min_) / self.scale_
        
    def inverse_transform(self, data):
        """Reverts the scaling."""
        if self.min_ is None or self.max_ is None:
            raise ValueError("Scaler has not been fitted yet.")
        return (data * self.scale_) + self.min_
