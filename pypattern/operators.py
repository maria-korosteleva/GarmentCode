"""Shortcuts for common operations on panels and components"""

from copy import deepcopy
import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize

# Custom 
from .component import Component
from .edge import LogicalEdge
from .connector import InterfaceInstance

# ANCHOR ----- Typical Edge Sequences generators ----
# TODO Do these routines belong in this module?

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


def side_with_cut(start=(0,0), end=(1,0), start_cut=0, end_cut=0):
    """ Edge with internal vertices that allows to stitch only part of the border represented
        by the long side edge

        start_cut and end_cut specify the fraction of the edge to to add extra vertices at
    """
    # TODO Curvature support?

    nstart, nend = np.array(start), np.array(end)
    verts = [start]

    if start_cut > 0:
        verts.append((start + start_cut * (nend-nstart)).tolist())
    if end_cut > 0:
        verts.append((end - end_cut * (nend-nstart)).tolist())
    verts.append(end)

    edges = []
    for i in range(1, len(verts)):
        edges.append(LogicalEdge(verts[i-1], verts[i]))
    
    return edges


# DRAFT corner cutting
def cut_corner(target_shape, panel, eid1, eid2):
    """ Cut the corner made of edges 1 and 2 following the shape of target_shape
        This routine updated the panel geometry and interfaces appropriately

        Parameters:
        * 'target_shape' is a list that is expected to contain one LogicalEdge or sequence of chained LogicalEdges (next one starts from the end vertex of the one before)
        * Panel to modify
        * eid1, eid2 -- ids of the chained pairs of edges that form the corner to cut, s.t. the end vertex of eid1 is at the corner
           # NOTE: Onto edges are expected to be straight lines for simplicity
    """
    # TODO Problem with the edge orientations and stuff like that

    # TODO does the target_shape deforms or getting cut if if doesn't perfectly match the corner size?

    corner_shape = deepcopy(target_shape)
    # Get rid of directions by working on vertices
    vc = np.array(panel.edges[eid1].end)
    v1, v2 = np.array(panel.edges[eid1].start), np.array(panel.edges[eid2].end)
    if v1[1] > v2[1]:
        v1, v2 = v2, v1  
        # NOW v1 is lower then v2
    if corner_shape[0].start[1] > corner_shape[-1].end[1]:
        corner_shape.reverse()
        for e in corner_shape:
            e.flip()
        # now corner shape is oriented the same way as vertices

    shortcut = np.array([corner_shape[0].start, corner_shape[-1].end]) #  TODO as vector

    # DEBUG
    print(corner_shape[0].start, corner_shape[0].end)
    print(f'To Intersect: {shortcut}, {(v1, vc, v2)}')

    # find translation s.t. start of shortcut is on [v1,vc], and end of shortcut is on [v2,vc] -- as best as possible
    # SLE!!! LOL

    shift = minimize(
        _fit_transl_scale, np.zeros(4), args=(shortcut, v1, v2, vc, dist(v1, vc), dist(v2, vc)))

    shifted = shortcut + shift.x[:2]
    shifted[0] += (shifted[0] - shifted[1]) * shift.x[2]  # this only changes the end vertex though
    shifted[1] += (shifted[1] - shifted[0]) * shift.x[3]  # this only changes the end vertex though

    # DEBUG
    print(shifted)
    print(f'Predicted:  {shift.x}, func value {shift.fun}')  # {shortcut + shift},
    print(f'Predicted:  {shift}')  # {shortcut + shift},

    # shift = minimize(
    #     _fit_translation, np.zeros(2), args=(shortcut, v1, v2, vc, dist(v1, vc), dist(v2, vc)))

    # shifted = shortcut + shift.x

    # # DEBUG
    # print(shifted)
    # print(f'Predicted:  {shift.x}, func value {shift.fun}')  # {shortcut + shift},
    # print(f'Predicted:  {shift}')  # {shortcut + shift},

    # # Then, find scaling parameter that allows to place the end vertces exactly -- another SLE
    # # TODO IF
    # scale = minimize(
    #     _fit_scale, np.zeros(2), args=(shifted, v1, v2, vc, dist(v1, vc), dist(v2, vc)))

    # shifted[0] += (shifted[0] - shifted[1]) * scale.x[0]  # this only changes the end vertex though
    # shifted[1] += (shifted[1] - shifted[0]) * scale.x[1]  # this only changes the end vertex though

    # # DEBUG
    # print(shifted)
    # print(f'Predicted:  {scale.x}, func value {scale.fun}')  # {shortcut + shift},
    # print(f'Predicted:  {scale}')  # {shortcut + shift},


def dist(v1, v2):
    return norm(v2-v1)

def _fit_translation(shift, shortcut, v1, v2, vc, d_v1, d_v2):
    """Evaluate how good a shortcut fits the corner with given global shift"""

    # TODO is it fast enoughs??
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = shortcut + shift

    return ((d_v1 - dist(shifted[0], v1) - dist(shifted[0], vc))**2
            + (d_v2 - dist(shifted[1], v2) - dist(shifted[1], vc))**2
            )

def _fit_scale(s, shortcut, v1, v2, vc, d_v1, d_v2):
    """Evaluate how good a shortcut fits the corner if the vertices are shifted 
        a little along the line"""

    # TODO is it fast enoughs??
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = deepcopy(shortcut)
    shifted[0] += (shortcut[0] - shortcut[1]) * s[0]  # this only changes the end vertex though
    shifted[1] += (shortcut[1] - shortcut[0]) * s[1]  # this only changes the end vertex though

    print(shifted)

    return ((d_v1 - dist(shifted[0], v1) - dist(shifted[0], vc))**2
            + (d_v2 - dist(shifted[1], v2) - dist(shifted[1], vc))**2
            )

# Joint
def _fit_transl_scale(s, shortcut, v1, v2, vc, d_v1, d_v2):
    """Evaluate how good a shortcut fits the corner if the vertices are shifted 
        a little along the line"""

    # TODO is it fast enoughs??
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = deepcopy(shortcut)
    shifted += s[:2]
    shifted[0] += (shortcut[0] - shortcut[1]) * s[2]  # this only changes the end vertex though
    shifted[1] += (shortcut[1] - shortcut[0]) * s[3]  # this only changes the end vertex though

    print(shifted)

    return ((d_v1 - dist(shifted[0], v1) - dist(shifted[0], vc))**2
            + (d_v2 - dist(shifted[1], v2) - dist(shifted[1], vc))**2
            )





# DRAFT General projection idea
def project(edges, panel, edge_id):
    """Project the shape defines by edges onto the panel's specified edge.
        This routine updated the panel geometry and interfaces appropriately

        NOTE: 'edges' are expected to contain one edge or sequence of chained edges (next one starts from the end vertex of the one before)
    """

    # TODO Same for components -- what if there are some interfaces that this panel is conneced to already?
    # TODO Projection location? 
    # TODO Direction
    # TODO adjustment for 2D rotation? Project rotated version? Might be important for sleeves
    
    base_edge = panel.edges[edge_id]

    # DEBUG
    print(f'Base edge vertices: {base_edge.start}, {base_edge.end}')
    # DEBUG
    print(f'Edges to insert: {[(e.start, e.end) for e in edges]}')

    # Create new edges
    edges_copy = [deepcopy(e) for e in edges]

    # TODO with a shift? 
    # TODO from the start??
    shift = [base_edge.start[0] - edges_copy[0].start[0], base_edge.start[0] - edges_copy[0].start[0]]
    edges_copy[0].start = base_edge.start  # start with the same vertex as target edge

    for e in edges_copy:  # NOTE this part assumes that edges are chained
        e.end[0] += shift[0]
        e.end[1] += shift[1]

    # Connect with the rest of the edges
    edges_copy.append(LogicalEdge(edges_copy[-1].end, base_edge.end))

    # DEBUG
    print(f'New edges: {[(e.start, e.end) for e in edges_copy]}')

    # Substitute edges in the panel definition
    panel.edges.pop(edge_id)
    for i, e in enumerate(edges_copy):
        panel.edges.insert(edge_id + i, e)

    # Update interface definitions
    intr_id = None
    for i, intr in enumerate(panel.interfaces):
        if intr.edge is base_edge:
            intr_id = i

    # Bunch of new interfaces
    if intr_id is not None:
        panel.interfaces.pop(intr_id)
        panel.interfaces += [InterfaceInstance(panel, e) for e in edges_copy]

    


# ANCHOR Panel operations 
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
