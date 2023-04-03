"""Shortcuts for common operations on panels and components"""

from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
import bezier
import matplotlib.pyplot as plt

# Custom 
from .edge import Edge, EdgeSequence
from .interface import Interface
from .generic_utils import vector_angle, close_enough
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
        * target_interface -- the chained pairs of edges that form the corner to cut, s.t. the end vertex of eid1 is at the corner
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

    if corner_shape[0].start is corner_shape[-1].end:
        # Orginal edges have beed reversed in normalization or smth
        corner_shape.edges.reverse()  # UPD the order

    if corner_shape[0].start[1] > corner_shape[-1].end[1]:
        # now corner shape is oriented the same way as vertices
        corner_shape.reverse()
        corner_shape.snap_to([0,0])

    shortcut = corner_shape.shortcut()

    # Curves  (can be defined outside)

    # DRAFT Version for straight edges
    # vc = np.array(target_edges[0].end)
    # v1, v2 = np.array(target_edges[0].start), np.array(target_edges[1].end)

    # swaped = False
    # if v1[1] > v2[1]:
    #     v1, v2 = v2, v1  
    #     swaped = True
    #     # NOW v1 is lower then v2

    # vec1 = np.asarray([v1, vc])
    # vec1 = vec1.transpose()
    # curve1 = bezier.Curve(np.asfortranarray(vec1), degree=1)

    # vec2 = np.asarray([v2, vc])  # for both 1==vc
    # vec2 = vec2.transpose()
    # curve2 = bezier.Curve(np.asfortranarray(vec2), degree=1)

    # TODO representation for sraight edges
    # TODO For circle arcs
    curve1 = target_edges[0].as_curve()
    curve2 = target_edges[1].as_curve()

    # align order with the a projecting shape, s.t. 
    # curve2 is alawys the lower one
    swaped = False
    if target_edges[0].start[1] > target_edges[-1].end[1]:
        curve1, curve2 = curve2, curve1
        swaped = True
        # NOW v1 is lower then v2

    # ----- FIND OPTIMAL PLACE -----
    start = [0.5, 0.5]
    out = minimize(
       _fit_location_corner, start, 
       args=(shortcut[1] - shortcut[0], curve1, curve2),
       bounds=[(0, 1), (0, 1)])
    
    # DEBUG
    print(out)

    if not out.success:
        raise RuntimeError(f'Cut_corner::Error::finding the projection (translation) is unsuccessful. Likely an error in edges choice')

    if not close_enough(out.fun):
        print(f'Cut_corner::Warning::projection on {target_interface} finished with fun={out.fun}')
        print(out) 

    loc = out.x
    point1 = curve1.evaluate(loc[0]).flatten()
    # re-align corner_shape with found shifts
    corner_shape.snap_to(point1)   
    
    # ----- UPD panel ----
    # Complete to the full corner -- connect with the initial vertices
    if swaped:
        # The edges are aligned as v2 -> vc -> v1
        corner_shape.reverse()
        loc[0], loc[1] = loc[1], loc[0]

    # Insert a new shape
    cut_edge1, _ = target_edges[0].subdivide([loc[0], 1-loc[0]])  # TODO order!
    _,  cut_edge2 = target_edges[1].subdivide([loc[1], 1-loc[1]])  # TODO order!
    
    cut_edge1.end = corner_shape[0].start  # Connect with new insert
    cut_edge2.start = corner_shape[-1].end

    corner_shape.insert(0, cut_edge1)
    corner_shape.append(cut_edge2)

    # Substitute edges in the panel definition
    panel.edges.pop(target_edges[0])
    panel.edges.substitute(target_edges[1], corner_shape)

    # Update interface definitions
    target_edges = EdgeSequence(target_edges.edges)  # keep the same edge references, 
                                                     # but not the same edge sequence reference
                                                     # In case it matches one of the interfaces (we don't want target edges to be overriden)
    iter = panel.interfaces if isinstance(panel.interfaces, list) else panel.interfaces.values() 
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

def cut_into_edge(target_shape, base_edge:Edge, offset=0, right=True, tol=1e-4):
    """ Insert edges of the target_shape into the given base_edge, starting from offset
        edges in target shape are rotated s.t. start -> end vertex vector is aligned with the edge 

        NOTE: for now the base_edge is treated as straight edge

        Parameters:
        * target_shape -- list of single edge or chained edges to be inserted in the edge. 
        * base_edge -- edge object, defining the border
        * right -- which direction the cut should be oriented w.r.t. the direction of base edge
        * Offset -- position of the center of the target shape along the edge.  

        Returns:
        * Newly created edges that accomodate the cut
        * Edges corresponding to the target shape
        * Edges that lie on the original base edge 
    """
    # TODO Allow insertion into curved edges
    target_shape = EdgeSequence(target_shape)
    new_edges = target_shape.copy().snap_to([0, 0])  # copy and normalize translation of vertices

    # Simplify to vectors
    shortcut = new_edges.shortcut()  # "Interface" of the shape to insert
    target_shape_w = norm(shortcut)
    edge_vec = np.array([base_edge.start, base_edge.end])  
    edge_len = base_edge.length()

    if offset < target_shape_w / 2 or offset > (edge_len - target_shape_w / 2):   
        raise ValueError(f'Operators-CutingIntoEdge::Error::offset value is not within the base_edge length')

    # find starting vertex for insertion & place edges there
    # DRAFT rel_offset = (offset - target_shape_w / 2) / edge_len   # relative to the length of the base edge
    rel_offset = offset / edge_len   # relative to the length of the base edge


    # ----- OPTIMIZATION --- 
    curve = base_edge.as_curve()
    start = [0]
    out = minimize(
       _fit_location_edge, start, 
       args=(rel_offset, target_shape_w, curve),
       bounds=[(0, 1)])
    
    # DEBUG
    print(out)

    # DRAFT if not out.success:
    #     raise RuntimeError(f'Cut_corner::Error::finding the projection (translation) is unsuccessful. Likely an error in edges choice')

    if not close_enough(out.fun):
        print(f'Cut_corner::Warning::projection on {base_edge} finished with fun={out.fun}')
        print(out) 

    wshift = out.x[0]

    # DRAFT ins_point = rel_offset * (edge_vec[1] - edge_vec[0]) + edge_vec[0] if rel_offset > tol else base_edge.start   

    ins_point = curve.evaluate(rel_offset - wshift).flatten() if (rel_offset - wshift) > tol else base_edge.start
    fin_point = curve.evaluate(rel_offset + wshift).flatten() if (rel_offset + wshift) < edge_len - tol else base_edge.end

    # DEBUG
    print('In the edge: ', base_edge.start, base_edge.end)
    print('Dart placement: ', ins_point, fin_point)

    # Align the shape with an edge
    # find rotation to apply on target shape 
    insert_vector = np.asarray(fin_point) - np.asarray(ins_point)
    angle = vector_angle(insert_vector, shortcut[1] - shortcut[0])
    new_edges.rotate(angle) 

    # DEBUG
    print('Rotated: ', new_edges)

    # place
    new_edges.snap_to(ins_point)
    # DEBUG
    print('Shifted: ', new_edges)

    # Check orientation 
    avg_vertex = np.asarray(new_edges.verts()).mean(0)
    right_position = np.sign(np.cross(insert_vector, avg_vertex - np.asarray(new_edges[0].start))) == -1 
    if not right and right_position or right and not right_position:
        # flip shape to match the requested direction
        new_edges.reflect(new_edges[0].start, new_edges[-1].end)

    # re-create edges and return 
    # NOTE: no need to create extra edges if the the shape is incerted right at the beggining or end of the edge
    base_edge_leftovers = EdgeSequence()
    start_id, end_id = 0, len(new_edges)

    if offset > target_shape_w / 2 + tol:  
        # TODO more elegant subroutine
        start_part = base_edge.subdivide([rel_offset - wshift, 1 - (rel_offset - wshift)])[0]
        start_part.end = new_edges[0].start
        new_edges.insert(0, start_part)
        base_edge_leftovers.append(new_edges[0])
        start_id = 1 
    
    if offset < (edge_len - target_shape_w / 2) - tol:
        end_part = base_edge.subdivide([rel_offset + wshift, 1 - (rel_offset + wshift)])[-1]
        end_part.start = new_edges[-1].end
        new_edges.append(end_part)
        base_edge_leftovers.append(new_edges[-1])
        end_id = -1
    
    print('Merges side: ', new_edges)  # DEBUG

    return new_edges, new_edges[start_id:end_id], base_edge_leftovers

# ANCHOR ----- Panel operations ------
def distribute_Y(component, n_copies, odd_copy_shift=10):
    """Distribute copies of component over the circle around Oy"""
    copies = [ component ]
    delta_rotation = R.from_euler('XYZ', [0, 360 / n_copies, 0], degrees=True)
    
    for i in range(n_copies - 1):
        new_component = deepcopy(copies[-1])
        new_component.name = f'panel_{i}'   # Unique
        new_component.rotate_by(delta_rotation)
        new_component.translate_to(delta_rotation.apply(new_component.translation))

        copies.append(new_component)

    # shift around to resolve collisions (hopefully)
    if odd_copy_shift:
        for i in range(n_copies):
            if not i % 2:
                copies[i].translate_by(copies[i].norm() * odd_copy_shift)
        
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

def _fit_location_corner(l, diff_target, curve1, curve2):
    """Find the points on two curves s.t. vector between them is the same as shortcut"""

    # Current points on curves
    point1 = curve1.evaluate(l[0]).flatten()
    point2 = curve2.evaluate(l[1]).flatten()
    diff_curr = point2 - point1

    # DEBUG
    # points = np.vstack((point1, point2))
    # points = points.transpose()
    # ax1 = curve1.plot(40)
    # _ = curve2.plot(40, ax=ax1)
    # lines = ax1.plot(  
    #     points[0, :], points[1, :],
    #     marker="o", linestyle="None", color="black")
    # plt.show()

    # DEBUG   
    print(diff_curr, diff_target)
    print('Location Progression: ', (diff_curr[0] - diff_target[0])**2, (diff_curr[1] - diff_target[1])**2)

    return ((diff_curr[0] - diff_target[0])**2 
            + (diff_curr[1] - diff_target[1])**2)


def _fit_location_edge(l_shift, location, width_target, curve):
    """Find the points on two curves s.t. vector between them is the same as shortcut"""

    # Current points on curves
    point1 = curve.evaluate(location + l_shift[0]).flatten()
    point2 = curve.evaluate(location - l_shift[0]).flatten()
    diff_curr = point2 - point1

    # DEBUG
    points = np.vstack((point1, point2))
    points = points.transpose()
    ax1 = curve.plot(40)
    lines = ax1.plot(  
        points[0, :], points[1, :],
        marker="o", linestyle="None", color="black")
    plt.show()

    # DEBUG   
    print(diff_curr, width_target)
    print('Location Progression: ', (_dist(point1, point2) - width_target)**2)

    return (_dist(point1, point2) - width_target)**2

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
