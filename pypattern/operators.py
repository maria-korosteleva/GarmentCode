"""Shortcuts for common operations on panels and components"""

from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize

# Custom 
from .edge import Edge, EdgeSequence
from .interface import Interface
from ._generic_utils import vector_angle, close_enough
from .base import BaseComponent

# ANCHOR ----- Edge Sequences Modifiers ----
def cut_corner(target_shape:EdgeSequence, target_interface:Interface):
    """ Cut the corner made of edges 1 and 2 following the shape of target_shape
        This routine updated the panel geometry and interfaces appropriately

        Parameters:
        * 'target_shape' is an EdgeSequence that is expected to contain one Edge or sequence of chained Edges 
            (next one starts from the end vertex of the one before)
            # NOTE: 'target_shape' might be scaled (along the main direction) to fit the corner size
        * Panel to modify
        * target_edges -- the chained pairs of edges that form the corner to cut, s.t. the end vertex of eid1 is at the corner
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
    # TODO Support any number of edges in the target corner edges

    # ---- Evaluate optimal projection of the target shape onto the corner
    corner_shape = target_shape.copy()
    panel = target_interface.panel[0]   # TODO Support multiple panels???
    target_edges = target_interface.edges
    
    # Get rid of directions by working on vertices
    if target_edges[0].start is target_edges[-1].end:
        # Orginal edges have beed reversed in normalization or smth
        target_edges.edges.reverse()  # UPD the order

    vc = np.array(target_edges[0].end)
    v1, v2 = np.array(target_edges[0].start), np.array(target_edges[1].end)
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
    shift = out.x

    # re-align corner_shape with found shifts
    corner_shape.snap_to([
        corner_shape[0].start[0] + shift[0], 
        corner_shape[0].start[1] + shift[1]
        ])
    
    # ----- UPD panel ----
    # Complete to the full corner -- connect with the initial vertices
    if swaped:
        # The edges are aligned as v2 -> vc -> v1
        corner_shape.reverse()

    corner_shape.insert(0, Edge(target_edges[0].start, corner_shape[0].start))
    corner_shape.append(Edge(corner_shape[-1].end, target_edges[1].end))

    # Substitute edges in the panel definition
    panel.edges.pop(target_edges[0])
    panel.edges.substitute(target_edges[1], corner_shape)

    # Update interface definitions
    target_edges = EdgeSequence(target_edges.edges)  # keep the same edge references, 
                                                     # but not the same edge sequence reference
                                                     # In case it matches one of the interfaces (we don't want target edges to be overriden)
    iter = panel.interfaces if isinstance(panel.interfaces, list) else panel.interfaces.values()   # TODO Uniform interfaces list
    for intr in iter:
        # Substitute old edges with what's left from them after cutting
        if target_edges[0] in intr.edges:
            intr.edges.substitute(target_edges[0], corner_shape[0])
        if target_edges[1] in intr.edges:
            intr.edges.substitute(target_edges[1], corner_shape[-1])

    # Add new interface corresponding to the introduced cut
    new_int = Interface(panel, corner_shape[1:-1])
    if isinstance(panel.interfaces, list):
        panel.interfaces.append(new_int)
    else:
        panel.interfaces[f'int_{len(panel.interfaces)}'] = new_int   # TODO Uniqueness of the name?

    return corner_shape[1:-1], new_int

def cut_into_edge(target_shape, base_edge, offset=0, right=True, tol=1e-4):
    """ Insert edges of the target_shape into the given base_edge, starting from offset
        edges in target shape are rotated s.t. start -> end vertex vector is aligned with the edge 

        NOTE: for now the base_edge is treated as straight edge

        Parameters:
        * target_shape -- list of single edge or chained edges to be inserted in the edge. 
        * base_edge -- edge object, defining the border
        * right -- which direction the cut should be oriented w.r.t. the direction of base edge
        * Offset -- position of the center of the target shape along the edge.   # TODO Update other uses of offser (godet skirt)

        Returns:
        * Newly created edges that accomodate the cut
        * Edges corresponding to the target shape
        * Edges that lie on the original base edge 
    """
    # TODO Allow insertion into curved edges
    target_shape = EdgeSequence(target_shape)
    new_edges = target_shape.copy().snap_to([0, 0])  # copy and normalize translation of vertices

    # Simplify to vectors
    shortcut = np.array([new_edges[0].start, new_edges[-1].end])  # "Interface" of the shape to insert
    target_shape_w = norm(shortcut)
    edge_vec = np.array([base_edge.start, base_edge.end])  
    edge_len = norm(edge_vec[1] - edge_vec[0])

    if offset < target_shape_w / 2 or offset > (edge_len - target_shape_w / 2):   
        raise ValueError(f'Operators-CutingIntoEdge::Error::offset value is not within the base_edge length')

    # Align the shape with an edge
    # find rotation to apply on target shape 
    angle = vector_angle(edge_vec[1] - edge_vec[0], shortcut[1] - shortcut[0])
    new_edges.rotate(angle)

    # find starting vertex for insertion & place edges there
    rel_offset = (offset - target_shape_w / 2) / edge_len   # relative to the length of the base edge
    ins_point = rel_offset * (edge_vec[1] - edge_vec[0]) + edge_vec[0] if rel_offset > tol else base_edge.start    
    new_edges.snap_to(ins_point)

    # Check orientation 
    avg_vertex = np.asarray(new_edges.verts()).mean(0)
    right_position = np.sign(np.cross(edge_vec[1] - edge_vec[0], avg_vertex - np.asarray(new_edges[0].start))) == -1  # TODO Correct?
    if not right and right_position or right and not right_position:
        # flip shape to match the requested direction
        new_edges.reflect(new_edges[0].start, new_edges[-1].end)

    # re-create edges and return 
    # NOTE: no need to create extra edges if the the shape is incerted right at the beggining or end of the edge
    base_edge_leftovers = EdgeSequence()
    start_id, end_id = 0, len(new_edges)
    if offset > target_shape_w / 2 + tol:  
        new_edges.insert(0, Edge(base_edge.start, new_edges[0].start))
        base_edge_leftovers.append(new_edges[0])
        start_id = 1 
    
    if offset < (edge_len - target_shape_w / 2) - tol:
        new_edges.append(Edge(new_edges[-1].end, base_edge.end))
        base_edge_leftovers.append(new_edges[-1])
        end_id = -1

    return new_edges, new_edges[start_id:end_id], base_edge_leftovers

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
        translation_dir = component.rotation.apply([0, 0, 1])   # Horisontally along the panel
        # FIXME What if it's looking up?
        translation_dir = np.cross(translation_dir, [0, 1, 0])   # perpendicular to Y
        translation_dir = translation_dir / norm(translation_dir)
        delta_translation = translation_dir * stride
    else:
        translation_dir = [1, 0, 0] 

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
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = shortcut + shift

    return ((d_v1 - _dist(shifted[0], v1) - _dist(shifted[0], vc))**2
            + (d_v2 - _dist(shifted[1], v2) - _dist(shifted[1], vc))**2
            )


def _fit_scale(s, shortcut, v1, v2, vc, d_v1, d_v2):
    """Evaluate how good a shortcut fits the corner if the vertices are shifted 
        a little along the line"""
    # Shortcut can be used as 2D vector, not a set of 2D points, e.g.
    shifted = deepcopy(shortcut)
    shifted[0] += (shortcut[0] - shortcut[1]) * s[0]  # this only changes the end vertex though
    shifted[1] += (shortcut[1] - shortcut[0]) * s[1]  # this only changes the end vertex though

    return ((d_v1 - _dist(shifted[0], v1) - _dist(shifted[0], vc))**2
            + (d_v2 - _dist(shifted[1], v2) - _dist(shifted[1], vc))**2
            )
