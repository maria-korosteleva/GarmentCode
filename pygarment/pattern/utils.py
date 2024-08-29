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

def c_to_list(num):
    """Convert complex number to a list of 2 elements
        Allows processing of lists of complex numbers
    """

    if isinstance(num, (list, tuple, set, np.ndarray)):
        return [c_to_list(n) for n in num]
    else:
        return [num.real, num.imag]
    
def close_enough(f1, f2=0, tol=1e-4):
    """Compare two floats correctly """
    return abs(f1 - f2) < tol

# Vector local coodinates conversion
def rel_to_abs_2d(start, end, rel_point):
    """
        Converts coordinates expressed in a coordinate frame local
        to the edge [start, end] into edge vertices (global) coordinate frame
    """

    start, end = np.array(start), np.array(end)  # in case inputs are lists/tuples
    edge = end - start
    edge_perp = np.array([-edge[1], edge[0]])

    abs_start = start + rel_point[0] * edge
    abs_point = abs_start + rel_point[1] * edge_perp

    return abs_point

def abs_to_rel_2d(start, end, abs_point, as_vector=False):
    """
        Converts coordinates expressed in a global coordinate frame into 
        a frame local to the edge [start, end] 
    """

    start, end, abs_point = np.array(start), np.array(end), \
        np.array(abs_point)

    rel_point = [None, None]
    edge_vec = end - start
    edge_len = np.linalg.norm(edge_vec)
    point_vec = abs_point if as_vector else abs_point - start  # vector or point
    
    # X
    # project control_vec on edge_vec by dot product properties
    projected_len = edge_vec.dot(point_vec) / edge_len 
    rel_point[0] = projected_len / edge_len
    # Y
    projected = edge_vec * rel_point[0]
    vert_comp = point_vec - projected  
    rel_point[1] = np.linalg.norm(vert_comp) / edge_len

    # Distinguish left&right curvature
    rel_point[1] *= np.sign(np.cross(edge_vec, point_vec))

    return np.asarray(rel_point)
