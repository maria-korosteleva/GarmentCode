# Custom
import pypattern as pyp


# Collar shapes withough extra panels
def VNeckHalf(depth, width):
    """Simple VNeck design"""

    edges = pyp.EdgeSequence(pyp.Edge([0, 0], [width / 2,-depth]))
    
    return edges


def SquareNeckHalf(depth, width):
    """Simple VNeck design"""

    edges = pyp.esf.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    
    return edges