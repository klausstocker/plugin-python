import numpy as np


def column_means(values: np.ndarray) -> np.ndarray:
    return np.mean(values, axis=0)
