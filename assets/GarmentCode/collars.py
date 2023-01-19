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

    # TODO special case when angle = 180 (sin = 0)
    angle = np.deg2rad(angle)

    edges = pyp.esf.from_verts([0, 0], [-depth * np.cos(angle) / np.sin(angle), -depth], [width / 2, -depth])

    # DEBUG
    print('Collar! ', edges)
    print(np.tan(angle), np.sin(angle), np.cos(angle))
    
    return edges