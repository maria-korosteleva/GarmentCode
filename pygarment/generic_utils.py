from typing import TypeVar, Generic, Sequence, Callable

import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation
import svgpathtools as svgpath



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
    
    if abs(cross) > 1e-5:
        angle *= np.sign(cross)
    return angle


def R2D(angle):
    """2D rotation matrix by an angle"""
    return np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])


def vector_align_3D(v1, v2):
    """Find a rotation to align v1 with v2"""

    v1, v2 = np.asarray(v1), np.asarray(v2)
    cos = np.dot(v1, v2) / (norm(v1) * norm(v2))
    cos = max(min(cos, 1), -1)  # NOTE: getting rid of numbers like 1.000002 that appear due to numerical instability

    angle = np.arccos(cos) 

    # Cross to get the axis of rotation
    cross = np.cross(v1, v2)
    cross = cross / norm(cross)

    return Rotation.from_rotvec(cross * angle)


def close_enough(f1, f2=0, tol=1e-4):
    """Compare two floats correctly """
    return abs(f1 - f2) < tol


def bbox_paths(paths):
    """Bounding box of a list of paths/Edge Sequences"""

    bboxes = np.array([p.bbox() for p in paths])
    return (min(bboxes[:, 0]), max(bboxes[:, 1]),
            min(bboxes[:, 2]), max(bboxes[:, 3]))


def lin_interpolation(val1, val2, factor):
    """Linear interpolation between val1 and val2 with factor [0, 1]

    with factor == 0, output is val1
    with factor == 1, output is val2
    """
    if factor < 0 or factor > 1:
        raise ValueError(f'lin_interpolation::ERROR::Expected a factor \in [0, 1], got {factor}')

    return (1 - factor) * val1 + factor * val2


# ---- Complex numbers converters ----- 
def c_to_list(num):
    """Convert complex number to a list of 2 elements
        Allows processing of lists of complex numbers
    """

    if isinstance(num, (list, tuple, set, np.ndarray)):
        return [c_to_list(n) for n in num]
    else: 
        return [num.real, num.imag]


def c_to_np(num):
    """Convert complex number to a numpy array of 2 elements
        Allows processing of lists of complex numbers
    """
    if isinstance(num, (list, tuple, set, np.ndarray)):
        return np.asarray([c_to_list(n) for n in num])
    else: 
        return np.asarray([num.real, num.imag])


def list_to_c(num):
    """Convert 2D list or list of 2D lists into complex number/list of complex
    numbers"""
    if isinstance(num[0], (list, tuple, set, np.ndarray)):
        return [complex(n[0], n[1]) for n in num]
    else: 
        return complex(num[0], num[1])


# ---- Nested Dictionaries shortcuts ---- 
# https://stackoverflow.com/a/37704379
def nested_get(dic, keys):    
    for key in keys:
        dic = dic[key]
    return dic


def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def nested_del(dic, keys):
    for key in keys[:-1]:
        dic = dic[key]
    del dic[keys[-1]]


# ----- Curves ----- 
def curve_extreme_points(curve, on_x=False, on_y=True):
    """Return extreme points of the current edge
        NOTE: this does NOT include the border vertices of an edge
    """
    # Variation of https://github.com/mathandy/svgpathtools/blob/5c73056420386753890712170da602493aad1860/svgpathtools/bezier.py#L197
    poly = svgpath.bezier2polynomial(curve, return_poly1d=True)

    x_extremizers, y_extremizers = [], []
    if on_y:
        y = svgpath.imag(poly)
        dy = y.deriv()

        y_extremizers = svgpath.polyroots(dy, realroots=True,
                                          condition=lambda r: 0 < r < 1)
    if on_x:
        x = svgpath.real(poly)
        dx = x.deriv()
        x_extremizers = svgpath.polyroots(dx, realroots=True,
                                          condition=lambda r: 0 < r < 1)
    all_extremizers = x_extremizers + y_extremizers

    extreme_points = np.array([c_to_list(curve.point(t))
                               for t in all_extremizers])

    return extreme_points
