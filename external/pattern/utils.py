"""Generic utility functions"""

import numpy as np

def list_to_c(num):
    """Convert 2D list or list of 2D lists into complex number/list of complex numbers"""
    if isinstance(num[0], list) or isinstance(num[0], np.ndarray):
        return [complex(n[0], n[1]) for n in num]
    else: 
        return complex(num[0], num[1])
    
def c_to_np(num):
    """Convert complex number to a numpy array of 2 elements"""
    return np.asarray([num.real, num.imag])

def vector_angle(v1, v2):
    """Find an angle between two 2D vectors"""
    v1, v2 = np.asarray(v1), np.asarray(v2)
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos = max(min(cos, 1), -1)  # NOTE: getting rid of numbers like 1.000002 that appear due to numerical instability
    angle = np.arccos(cos) 
    # Cross to indicate correct relative orienataion of v2 w.r.t. v1
    cross = np.cross(v1, v2)
    
    if abs(cross) > 1e-5:
        angle *= np.sign(cross)
    return angle
