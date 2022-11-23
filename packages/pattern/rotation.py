"""
    Simple Rotation Conversion routines (Maya-Python2.7-Compatible!!)
    TODO: Can be substituted with scipy rotation transformation routines for Maya2022+
"""
import numpy as np
import math as m
import sys


# Thanks to https://www.meccanismocomplesso.org/en/3d-rotations-and-euler-angles-in-python/ for the code
def _Rx(theta):
    return np.matrix([
        [1, 0           , 0           ],
        [0, m.cos(theta), -m.sin(theta)],
        [0, m.sin(theta), m.cos(theta)]])


def _Ry(theta):
    return np.matrix([
        [m.cos(theta), 0, m.sin(theta)],
        [0           , 1, 0           ],
        [-m.sin(theta), 0, m.cos(theta)]])


def _Rz(theta):
    return np.matrix([
        [m.cos(theta), -m.sin(theta), 0],
        [m.sin(theta), m.cos(theta) , 0],
        [0           , 0            , 1]])


def euler_xyz_to_R(euler):
    """Convert to Rotation matrix.
        Expects input in degrees.
        Only support Maya convension of intrinsic xyz Euler Angles
    """
    return _Rz(np.deg2rad(euler[2])) * _Ry(np.deg2rad(euler[1])) * _Rx(np.deg2rad(euler[0]))


def R_to_euler(R):
    """
        Convert Rotation matrix to Euler-angles in degrees (in Maya convension of intrinsic xyz Euler Angles)
        NOTE: 
            Routine produces one of the possible Euler angles, corresponding to input rotations (the Euler angles are not uniquely defined)
    """
    tol = sys.float_info.epsilon * 10
  
    if abs(R[0, 0]) < tol and abs(R[1, 0]) < tol:
        eul1 = 0
        eul2 = m.atan2(-R[2, 0], R[0, 0])
        eul3 = m.atan2(-R[1, 2], R[1, 1])
    else:   
        eul1 = m.atan2(R[1, 0], R[0, 0])
        sp = m.sin(eul1)
        cp = m.cos(eul1)
        eul2 = m.atan2(-R[2, 0], cp * R[0, 0] + sp * R[1, 0])
        eul3 = m.atan2(sp * R[0, 2] - cp * R[1, 2], cp * R[1, 1] - sp * R[0, 1])
    
    return [np.rad2deg(eul3), np.rad2deg(eul2), np.rad2deg(eul1)]

