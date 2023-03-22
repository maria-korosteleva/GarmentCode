import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation
from typing import TypeVar, Generic, Sequence, Callable


# proper inserstions by key with bicest module in python <3.10
# https://stackoverflow.com/questions/27672494/how-to-use-bisect-insort-left-with-a-key

T = TypeVar('T')
V = TypeVar('V')

class KeyWrapper(Generic[T, V]):
    def __init__(self, iterable: Sequence[T], key: Callable[[T], V]):
        self.it = iterable
        self.key = key

    def __getitem__(self, i: int) -> V:
        return self.key(self.it[i])

    def __len__(self) -> int:
        return len(self.it)

def vector_angle(v1, v2):
    """Find an angle between two 2D vectors"""
    v1, v2 = np.asarray(v1), np.asarray(v2)
    cos = np.dot(v1, v2) / (norm(v1) * norm(v2))
    angle = np.arccos(cos) 
    # Cross to indicate correct relative orienataion of v2 w.r.t. v1
    cross = np.cross(v1, v2)
    if cross > 1e-5:
        angle *= np.sign(cross)
    return angle

def R2D(angle):
    """2D rotation matrix by an angle"""
    return np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])

def vector_align_3D(v1, v2):
    """Find a rotation to align v1 with v2"""

    v1, v2 = np.asarray(v1), np.asarray(v2)
    cos = np.dot(v1, v2) / (norm(v1) * norm(v2))
    angle = np.arccos(cos) 

    # Cross to get the axis of rotation
    cross = np.cross(v1, v2)
    cross = cross / norm(cross)

    return Rotation.from_rotvec(cross * angle)


def close_enough(f1, f2=0, tol=1e-4):
    """Compare two floats correctly """
    return abs(f1 - f2) < tol