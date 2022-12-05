"""Shortcuts for common operations on panels and components"""

from copy import deepcopy
import numpy as np
from scipy.spatial.transform import Rotation as R

# Custom 
from .component import Component
from .edge import LogicalEdge

# ----- Typical Edge Sequences generators ----

def simple_loop(*verts):
    """Generate edge sequence -- looped from sequence of vertices
        Assume that the first vertex is always at origin
    """
    # TODO what's with the ruffle coefficients?
    # TODO Curvatures
    # TODO Use other edge sequential generators?
    # TODO Connect with previous edge in the edge class itself?
    edges = [
        LogicalEdge([0,0], verts[0])
    ]
    for i in range(1, len(verts)):
        edges.append(LogicalEdge(edges[-1].end, verts[i]))
    edges.append(LogicalEdge(edges[-1].end, edges[0].start))

    return edges


# TODO Does it belong in this module?
def side_with_cut(start=(0,0), end=(1,0), start_cut=0, end_cut=0):
    """ Edge with internal vertices that allows to stitch only part of the border represented
        by the long side edge

        start_cut and end_cut specify the fraction of the edge to to add extra vertices at
    """
    # TODO Curvature support?

    nstart, nend = np.array(start), np.array(end)
    verts = [start]

    if start_cut > 0:
        verts.append(tuple(start + start_cut * (nend-nstart)))
    if end_cut > 0:
        verts.append(tuple(end - end_cut * (nend-nstart)))
    verts.append(end)

    edges = []
    for i in range(1, len(verts)):
        edges.append(LogicalEdge(verts[i-1], verts[i]))
    
    return edges


# On Panels
def distribute_Y(component: Component, n_copies: int):
    """Distribute copies of component over the circle around Oy"""
    copies = [ component ]
    for i in range(n_copies - 1):
        new_component = deepcopy(copies[-1])
        new_component.name = f'panel_{i}'   # Unique
        delta_rotation = R.from_euler('XYZ', [0, 360 / n_copies, 0], degrees=True)

        new_component.rotate_by(delta_rotation)
        new_component.translation = delta_rotation.apply(new_component.translation)

        copies.append(new_component)

    return copies