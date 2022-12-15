"""Shortcuts for common operations on panels and components"""

from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize

# Custom 
from .edge import LogicalEdge, EdgeSequence
from .interface import Interface
from ._generic_utils import vector_angle
from .base import BaseComponent

# ANCHOR ----- Edge Sequences Modifiers ----
# TODO also part of EdgeSequence class?

def cut_corner(target_shape:EdgeSequence, panel, eid1, eid2):
    """ Cut the corner made of edges 1 and 2 following the shape of target_shape
        This routine updated the panel geometry and interfaces appropriately

        Parameters:
        * 'target_shape' is an EdgeSequence that is expected to contain one LogicalEdge or sequence of chained LogicalEdges 
            (next one starts from the end vertex of the one before)
            # NOTE: 'target_shape' might be scaled (along the main direction) to fit the corner size
        * Panel to modify
        * eid1, eid2 -- ids of the chained pairs of edges that form the corner to cut, s.t. the end vertex of eid1 is at the corner
            # NOTE: Onto edges are expected to be straight lines for simplicity

        # NOTE There might be slight computational errors in the resulting shape, 
                that are more pronounced on svg visualizations due to scaling and rasterization

        Side-Effects:
            * Modified the panel shape to insert new edges
            * Adds new interface object corresponding to new edges to the panel interface list

        Returns:
            * Newly inserted edges
            * New interface object corresponding to new edges
    """
    # TODO specifying desired 2D rotation of target_shape?
    # TODO component on component?? Interface / stitching rules re-calibration probelem

    # ---- Evaluate optimal projection of the target shape onto the corner
    corner_shape = target_shape.copy()
    # Get rid of directions by working on vertices
    vc = np.array(panel.edges[eid1].end)
    v1, v2 = np.array(panel.edges[eid1].start), np.array(panel.edges[eid2].end)
    swaped = False
    if v1[1] > v2[1]:
        v1, v2 = v2, v1  
        swaped = True
        # NOW v1 is lower then v2

    if corner_shape[0].start[1] > corner_shape[-1].end[1]:
        # now corner shape is oriented the same way as vertices
        corner_shape.reverse()

    shortcut = np.array([corner_shape[0].start, corner_shape[-1].end]) 

    # find translation s.t. start of shortcut is on [v1,vc], and end of shortcut is on [v2,vc] -- as best as possible
    # SLE!!! LOL
    out = minimize(
        _fit_translation, np.zeros(2), args=(shortcut, v1, v2, vc, _dist(v1, vc), _dist(v2, vc)))
    if not out.success:
        raise RuntimeError(f'Cut_corner::Error::finding the projection (translation) is unsuccessful. Likely an error in edges choice')
    shifted = shortcut + out.x
    shift = out.x

    # re-align corner_shape with found shifts
    corner_shape.snap_to([
        corner_shape[0].start[0] + shift[0], 
        corner_shape[0].start[1] + shift[1]
        ])

    # Then, find scaling parameter that allows to place the end vertces exactly -- another SLE
    if abs(out.fun) > 1e-3:  
        # TODO this part is NOT properly tested!!!! 

        # Fit with translation is not perfect -- try to adjust the length
        out = minimize(
            _fit_scale, np.zeros(2), args=(shifted, v1, v2, vc, _dist(v1, vc), _dist(v2, vc)))
        if not out.success:
            raise RuntimeError(f'Cut_corner::Error::finding the projection (scaling) is unsuccessful. Likely an error in edges choice')

        shifted[0] += (shifted[0] - shifted[1]) * out.x[0]
        shifted[1] += (shifted[1] - shifted[0]) * out.x[1]  

        # DEBUG
        print(f'Cut_corner::WARNING!!::Using untested re-scaling of edges')
        print(shifted)
        print(f'Predicted:  {out.x}, func value {out.fun}')  # {shortcut + shift},
        print(f'Predicted:  {out}')  # {shortcut + shift},

        scale = _dist(shifted[0], shifted[1]) / _dist(shortcut[1], shortcut[0])

        # move the sequence s.t. the initial vertex is places correctly
        corner_shape.snap_to((shifted[0] - shifted[1]) * out.x[0])

        # Move internal vertices according to predicred scale s.w. the final vertex can be placed correctly
        corner_shape.extend(scale)
    
    # ----- UPD panel ----
    # Complete to the full corner -- connect with the initial vertices
    if swaped:
        # The edges are aligned as v2 -> vc -> v1
        corner_shape.reverse()

    corner_shape.insert(0, LogicalEdge(panel.edges[eid1].start, corner_shape[0].start))
    corner_shape.append(LogicalEdge(corner_shape[-1].end, panel.edges[eid2].end))

    # Substitute edges in the panel definition
    edge1, edge2 = panel.edges[eid1], panel.edges[eid2]  # remember the old ones
    if eid2 < eid1:  # making sure that elements are removed in correct order
        eid1, eid2 = eid2, eid1
    panel.edges.pop(eid2)
    panel.edges.pop(eid1)   

    panel.edges.insert(eid1, corner_shape)

    # Update interface definitions
    for intr in panel.interfaces:
        # Substitute old edges with what's left from them after cutting
        if edge1 in intr.edges:
            intr.edges.substitute(edge1, corner_shape[0])
        if edge2 in intr.edges:
            intr.edges.substitute(edge2, corner_shape[-1])

    # Add new interface corresponding to the introduced cut
    panel.interfaces.append(Interface(panel, corner_shape[1:-1]))

    return corner_shape[1:-1], panel.interfaces[-1]

def cut_into_edge(target_shape, base_edge, offset=0, right=True, tol=1e-4):
    """ Insert edges of the target_shape into the given base_edge, starting from offset
        edges in target shape are rotated s.t. start -> end vertex vector is aligned with the edge 

        NOTE: for now the base_edge is treated as straight edge

        Parameters:
        * target_shape -- list of single edge or chained edges to be inserted in the edge. 
        * base_edge -- edge object, defining the border
        * right -- which direction the cut should be oriented w.r.t. the direction of base edge
        * Offset -- fraction [0, 1 - <target_shape_size>], defines position of the target shape along the edge.

        Returns:
        * Newly created edges that accomodate the cut
        * Edges corresponding to the cut area
    """
    # TODO Allow insertion into curved edges
    # TODO Is it needed? Or edge loop specification is enough?
    target_shape = EdgeSequence(target_shape)

    new_edges = target_shape.copy().snap_to([0, 0])  # copy and normalize translation of vertices

    # Simplify to vectors
    shortcut = np.array([new_edges[0].start, new_edges[-1].end])  # "Interface" of the shape to insert
    edge_vec = np.array([base_edge.start, base_edge.end])  

    if offset < 0 or offset > 1:   # TODO account also for the length of a shortcut
        raise ValueError(f'Operators-CutingIntoEdge::Error::offset value shoulf be between 0 and 1')

    # find rotation to apply on target shape to alight it with an edge
    angle = vector_angle(edge_vec[1] - edge_vec[0], shortcut[1] - shortcut[0])
    angle *= 1 if right else -1  # account for a desired orientation of the cut
    new_edges.rotate(angle)
    
    # find starting vertex for insertion & place edges there
    ins_point = offset * (edge_vec[1] - edge_vec[0]) + edge_vec[0] if offset > tol else base_edge.start    
    if right:  # We need to flip it's orientation of cut shape and then cut
        new_edges.reverse().snap_to([0, 0])  # new first vertex to be zero
    new_edges.snap_to(ins_point)

    # re-create edges and return 
    if offset > tol:
        new_edges.insert(0, LogicalEdge(base_edge.start, new_edges[0].start))
    
    # TODO Check if the end is not the same as base_edge already / goes beyong the end edge
    new_edges.append(LogicalEdge(new_edges[-1].end, base_edge.end))

    return new_edges, new_edges[1:-1]

# ANCHOR ----- Panel operations ------
def distribute_Y(component, n_copies):
    """Distribute copies of component over the circle around Oy"""
    copies = [ component ]
    for i in range(n_copies - 1):
        new_component = deepcopy(copies[-1])
        new_component.name = f'panel_{i}'   # Unique
        delta_rotation = R.from_euler('XYZ', [0, 360 / n_copies, 0], degrees=True)

        new_component.rotate_by(delta_rotation)
        new_component.translate_to(delta_rotation.apply(new_component.translation))

        copies.append(new_component)

    # TODO resolve collisions though!

    return copies


def distribute_horisontally(component, n_copies, stride=20, name_tag='panel'):
    """Distribute copies of component over the straight horisontal line perpendicular to the norm"""
    copies = [ component ]
    component.name = f'{name_tag}_0'   # Unique

    if isinstance(component, BaseComponent):
        translation_dir = component.rotation.apply([0, 0, 1])   # TODO panel norm
        # FIXME What if it's looking up?
        translation_dir = np.cross(translation_dir, [0, 1, 0])   # TODO control direction better?
        translation_dir = translation_dir / norm(translation_dir)
        delta_translation = translation_dir * stride
    else:
        translation_dir = [1, 0, 0]  # TODO specify?

    for i in range(n_copies - 1):
        new_component = deepcopy(copies[-1])   # TODO proper copy
        new_component.name = f'{name_tag}_{i + 1}'   # Unique
        new_component.translate_by(delta_translation)

        copies.append(new_component)

    # TODO resolve collisions though!

    return copies


# ---- Utils ----

def _dist(v1, v2):
    return norm(v2-v1)


def _fit_translation(shift, shortcut, v1, v2, vc, d_v1, d_v2):
    """Evaluate how good a shortcut fits the corner with given global shift"""

    # TODO is it fast enoughs??
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = shortcut + shift

    return ((d_v1 - _dist(shifted[0], v1) - _dist(shifted[0], vc))**2
            + (d_v2 - _dist(shifted[1], v2) - _dist(shifted[1], vc))**2
            )


def _fit_scale(s, shortcut, v1, v2, vc, d_v1, d_v2):
    """Evaluate how good a shortcut fits the corner if the vertices are shifted 
        a little along the line"""

    # TODO is it fast enoughs??
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = deepcopy(shortcut)
    shifted[0] += (shortcut[0] - shortcut[1]) * s[0]  # this only changes the end vertex though
    shifted[1] += (shortcut[1] - shortcut[0]) * s[1]  # this only changes the end vertex though

    return ((d_v1 - _dist(shifted[0], v1) - _dist(shifted[0], vc))**2
            + (d_v2 - _dist(shifted[1], v2) - _dist(shifted[1], vc))**2
            )
