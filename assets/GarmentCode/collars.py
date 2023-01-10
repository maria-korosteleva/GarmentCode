# Custom
import pypattern as pyp


# Collar shapes withough extra panels
# TODO I need here the matching interface for interchengeability ..
def VNeckHalf(tag, depth, width):
    """Simple VNeck design"""

    edges = pyp.EdgeSequence(pyp.Edge([0, 0], [width / 2,-depth]))
    
    return edges