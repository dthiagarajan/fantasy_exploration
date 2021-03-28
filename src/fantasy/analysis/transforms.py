from typing import Union

import numpy as np


def sigmoid(x: Union[float, np.ndarray]) -> np.ndarray:
    _x = x
    if isinstance(x, np.ndarray):
        _x = x.astype(float)
    return 1.0 / (1 + np.exp(-_x))
