import numpy as np

# Custom
import pypattern as pyp


# Collar shapes withough extra panels
def VNeckHalf(depth, width, **kwargs):
    """Simple VNeck design"""

    edges = pyp.EdgeSequence(pyp.Edge([0, 0], [width / 2,-depth]))
    
    return edges


def SquareNeckHalf(depth, width, **kwargs):
    """Square design"""

    edges = pyp.esf.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    
    return edges

def TrapezoidNeckHalf(depth, width, angle=90, **kwargs):
    """Trapesoid neck design"""

    # Special case when angle = 180 (sin = 0)
    if (pyp.utils.close_enough(angle, 180, tol=1) 
            or pyp.utils.close_enough(angle, 0, tol=1)):
        # degrades into VNeck
        return VNeckHalf(depth, width)

    angle = np.deg2rad(angle)

    edges = pyp.esf.from_verts([0, 0], [-depth * np.cos(angle) / np.sin(angle), -depth], [width / 2, -depth])

    return edges


# Collar shapes withough extra panels
def CurvyNeckHalf(depth, width, **kwargs):
    """Testing Curvy Collar design"""

    edges = pyp.EdgeSequence(pyp.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[0.4, 0.3], [0.8, -0.5]]))
    
    return edges


def CircleArcNeckHalf(depth, width, angle=90, **kwargs):
    """Collar with a side represented by a circle arc"""
    # 1/4 of a circle
    edges = pyp.EdgeSequence(pyp.CircleEdge.from_points_angle(
        [0, 0], [width / 2,-depth], arc_angle=np.deg2rad(angle),
        right=True
    ))

    return edges

def CircleNeckHalf(depth, width, **kwargs):
    """Collar that forms a perfect circle arc when halfs are stitched"""

    # Take a full desired arc and half it!
    circle = pyp.CircleEdge.from_three_points([0, 0], [width, 0], [width / 2, -depth])

    subdiv = circle.subdivide_len([0.5, 0.5])

    return pyp.EdgeSequence(subdiv[0])