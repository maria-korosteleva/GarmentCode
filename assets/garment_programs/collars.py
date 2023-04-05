import numpy as np

# Custom
import pypattern as pyp


# Collar shapes withough extra panels
def VNeckHalf(depth, width, *args):
    """Simple VNeck design"""

    edges = pyp.EdgeSequence(pyp.Edge([0, 0], [width / 2,-depth]))
    
    return edges


def SquareNeckHalf(depth, width, *args):
    """Square design"""

    edges = pyp.esf.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    
    return edges

def TrapezoidNeckHalf(depth, width, angle=90):
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
def CurvyNeckHalf(depth, width, *args):
    """Testing Curvy Collar design"""

    edges = pyp.EdgeSequence(pyp.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[0.4, 0.3], [0.8, -0.5]]))
    
    # DEBUG
    print(edges[0])
    print(edges[0].length())
    print(edges.length())

    # DEBUG
    # Testing shrinking/extention
    edges.extend(0.8)
    print('Adjusted length: ', edges.length())
    
    return edges


def CircleNeckHalf(depth, width, *args):
    """Testing Curvy Collar design"""

    # TODO it probably should be smarter -- to have flat tangent at the bottom at all times

    # 1/4 of a circle
    edges = pyp.EdgeSequence(pyp.CircleEdge.from_points_arc(
        [0, 0], [width / 2,-depth], arc_angle=np.pi / 2
    ))
    
    # DEBUG
    print(edges[0])
    print(edges[0].length())
    print(edges.length())

    # DEBUG
    # Testing shrinking/extention
    # edges.extend(0.8)
    # print('Adjusted length: ', edges.length())
    
    return edges