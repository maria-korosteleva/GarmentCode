"""Shortcuts for common operations on panels and components"""

from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import svgpathtools as svgpath

# Custom 
from .edge import Edge, CurveEdge, CircleEdge, EdgeSequence
from .interface import Interface
from .generic_utils import vector_angle, close_enough, c_to_list, c_to_np, list_to_c
from .base import BaseComponent
from . import flags

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
    # ---- Evaluate optimal projection of the target shape onto the corner
    corner_shape = target_shape.copy()
    panel = target_interface.panel[0]   
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
    curve1 = target_edges[0].as_curve()
    curve2 = target_edges[1].as_curve()

    # align order with the a projecting shape, s.t. 
    # curve2 is alawys the lower one
    swaped = False
    if target_edges[0].start[1] > target_edges[-1].end[1]:
        curve1, curve2 = curve2, curve1
        swaped = True
        # NOW curve1 is lower then curve2

    # ----- FIND OPTIMAL PLACE -----
    start = [0.5, 0.5]
    out = minimize(
       _fit_location_corner, start, 
       args=(shortcut[1] - shortcut[0], curve1, curve2),
       bounds=[(0, 1), (0, 1)])
    
    if flags.VERBOSE and not out.success:
        print(f'Cut_corner::Error::finding the projection (translation) is unsuccessful. Likely an error in edges choice')
        print(out)

    if flags.VERBOSE and not close_enough(out.fun):
        print(f'Cut_corner::Warning::projection on {target_interface} finished with fun={out.fun}')
        print(out) 

    loc = out.x
    point1 = c_to_list(curve1.point(loc[0]))
    # re-align corner_shape with found shifts
    corner_shape.snap_to(point1)   
    
    # ----- UPD panel ----
    # Complete to the full corner -- connect with the initial vertices
    if swaped:
        # The edges are aligned as v2 -> vc -> v1
        corner_shape.reverse()
        loc[0], loc[1] = loc[1], loc[0]

    # Insert a new shape
    cut_edge1, _ = target_edges[0].subdivide_param([loc[0], 1-loc[0]])
    _,  cut_edge2 = target_edges[1].subdivide_param([loc[1], 1-loc[1]])
    
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
        panel.interfaces[f'int_{len(panel.interfaces)}'] = new_int   

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
    target_shape = EdgeSequence(target_shape)
    new_edges = target_shape.copy().snap_to([0, 0])  # copy and normalize translation of vertices

    # Simplify to vectors
    shortcut = new_edges.shortcut()  # "Interface" of the shape to insert
    target_shape_w = norm(shortcut)
    edge_len = base_edge.length()

    if offset < target_shape_w / 2  - tol or offset > (edge_len - target_shape_w / 2) + tol:   
        # NOTE: This is not a definitive check, and the cut might still not fit, depending on the base_edge curvature
        raise ValueError(f'Operators-CutingIntoEdge::Error::offset value is not within the base_edge length')

    # find starting vertex for insertion & place edges there
    curve = base_edge.as_curve()
    rel_offset = curve.ilength(offset)   

    # ----- OPTIMIZATION --- 
    start = [0.1, 0.1]
    out = minimize(
       _fit_location_edge, start, 
       args=(rel_offset, target_shape_w, curve),
       bounds=[(0, 1)])
    shift = out.x  

    # Error checks
    if flags.VERBOSE and not out.success:
        print(f'Cut_edge::Error::finding the projection (translation) is unsuccessful. Likely an error in edges choice')

    if not close_enough(out.fun, tol=0.01):
        if flags.VERBOSE:
            print(out) 
        raise RuntimeError(f'Cut_edge::ERROR::projection on {base_edge} finished with fun={out.fun}')
    
    if rel_offset + shift[0] > 1 + tol or (rel_offset - shift[1]) < 0 - tol:
        raise RuntimeError(
            f'Cut_edge::ERROR::projection on {base_edge} is out of edge bounds: '
            f'[{rel_offset - shift[1], rel_offset + shift[0]}].'
            ' Check the offset value')

    # All good -- integrate the target shape
    ins_point = c_to_np(curve.point(rel_offset - shift[1])) if (rel_offset - shift[1]) > tol else base_edge.start
    fin_point = c_to_np(curve.point(rel_offset + shift[0])) if (rel_offset + shift[0]) < 1 - tol else base_edge.end

    # Align the shape with an edge
    # find rotation to apply on target shape 
    insert_vector = np.asarray(fin_point) - np.asarray(ins_point)
    angle = vector_angle(shortcut[1] - shortcut[0], insert_vector)
    new_edges.rotate(angle) 

    # place
    new_edges.snap_to(ins_point)

    # Check orientation 
    avg_vertex = np.asarray(new_edges.verts()).mean(0)
    right_position = np.sign(np.cross(insert_vector, avg_vertex - np.asarray(new_edges[0].start))) == -1 
    if not right and right_position or right and not right_position:
        # flip shape to match the requested direction
        new_edges.reflect(new_edges[0].start, new_edges[-1].end)  

    # Integrate edges
    # NOTE: no need to create extra edges if the the shape is incerted right at the beggining or end of the edge
    base_edge_leftovers = EdgeSequence()
    start_id, end_id = 0, len(new_edges)

    if ins_point is base_edge.start:
        new_edges[0].start = base_edge.start   # Connect into the original edge
    else:
        start_part = base_edge.subdivide_param([rel_offset - shift[1], 1 - (rel_offset - shift[1])])[0]
        start_part.end = new_edges[0].start
        new_edges.insert(0, start_part)
        base_edge_leftovers.append(new_edges[0])
        start_id = 1 

    if fin_point is base_edge.end:
        new_edges[-1].end = base_edge.end  # Connect into the original edge
    else:
        end_part = base_edge.subdivide_param([rel_offset + shift[0], 1 - (rel_offset + shift[0])])[-1]
        end_part.start = new_edges[-1].end
        new_edges.append(end_part)
        base_edge_leftovers.append(new_edges[-1])
        end_id = -1
        
    return new_edges, new_edges[start_id:end_id], base_edge_leftovers

def _fit_location_corner(l, diff_target, curve1, curve2):
    """Find the points on two curves s.t. vector between them is the same as shortcut"""

    # Current points on curves
    point1 = c_to_np(curve1.point(l[0]))
    point2 = c_to_np(curve2.point(l[1]))
    diff_curr = point2 - point1

    if flags.VERBOSE:
        print('Location Progression: ', (diff_curr[0] - diff_target[0])**2, (diff_curr[1] - diff_target[1])**2)

    return ((diff_curr[0] - diff_target[0])**2 
            + (diff_curr[1] - diff_target[1])**2)

def _fit_location_edge(shift, location, width_target, curve):
    """Find the points on two curves s.t. vector between them is the same as shortcut"""

    # Current points on curves
    pointc = c_to_np(curve.point(location))   
    point1 = c_to_np(curve.point(location + shift[0]))
    point2 = c_to_np(curve.point(location - shift[1]))


    if flags.VERBOSE:
        print('Location Progression: ', (_dist(point1, point2) - width_target)**2)

    # regularize points to be at the same distance from center
    reg_symmetry = (_dist(point1, pointc) - _dist(point2, pointc))**2

    return (_dist(point1, point2) - width_target)**2 + reg_symmetry


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
        translation_dir = np.cross(translation_dir, [0, 1, 0])   # perpendicular to Y
        translation_dir = translation_dir / norm(translation_dir)
        delta_translation = translation_dir * stride
    else:
        translation_dir = [1, 0, 0] 

    for i in range(n_copies - 1):
        new_component = deepcopy(copies[-1])  
        new_component.name = f'{name_tag}_{i + 1}'   # Unique
        new_component.translate_by(delta_translation)

        copies.append(new_component)

    return copies


# ANCHOR ----- Sleeve support -----
def even_armhole_openings(front_opening, back_opening, tol=1e-2):
    """
        Rearrange sleeve openings for front and back s.t. their projection 
        on vertical line is the same, while preserving the overall shape.
        Allows for creation of two symmetric sleeve panels from them

        !! Important: assumes that the front opening is longer then back opening
    """
    # Construct sleeve panel shapes from opening inverses
    cfront, cback = front_opening.copy(), back_opening.copy()
    cback.reflect([0, 0], [1, 0]).reverse().snap_to(cfront[-1].end)

    # Cutout
    slope = np.array([cfront[0].start, cback[-1].end])
    slope_vec = slope[1] - slope[0]
    slope_perp = np.asarray([-slope_vec[1], slope_vec[0]])
    slope_midpoint = (slope[0] + slope[1]) / 2

    # Intersection with the sleeve itself line
    # svgpath tools allow solution regardless of egde types
    inter_segment = svgpath.Line(
        list_to_c(slope_midpoint - 20 * slope_perp), 
        list_to_c(slope_midpoint + 20 * slope_perp)
    )
    target_segment = cfront[-1].as_curve()

    intersect_t = target_segment.intersect(inter_segment)
    if len(intersect_t) != 1:
        print(
            f'Sleeve Opening Inversion::Error::{len(intersect_t)} intersection points instead of one. '
            'Check the quality of supplied curves'
        )
    
    if (len(intersect_t) >= 1 
            and not (close_enough(intersect_t[0][0], 0, tol=tol)   # checking if they are already ok separated
                     or close_enough(intersect_t[0][0], 1, tol=tol))):
        # The current separation is not satisfactory
        # Update the opening shapes
        intersect_t = intersect_t[0][0]
        subdiv = front_opening.edges[-1].subdivide_param([intersect_t, 1 - intersect_t])
        front_opening.substitute(-1, subdiv[0])  

        # Move this part to the back opening
        subdiv[1].start, subdiv[1].end = copy(subdiv[1].start), copy(subdiv[1].end)  # Disconnect vertices in subdivided version
        subdiv.pop(0) 
        subdiv.reflect([0, 0], [1, 0]).reverse().snap_to(back_opening[-1].end)
        subdiv[0].start = back_opening[-1].end
        
        back_opening.append(subdiv[0])

    # Align the slope with OY direction
    # for correct size of sleeve panels
    slope_angle = np.arctan(-slope_vec[0] / slope_vec[1])	
    front_opening.rotate(-slope_angle)
    back_opening.rotate(slope_angle)

    return front_opening, back_opening

# ANCHOR ----- Curve tools -----
def _max_curvature(curve, points_estimates=100):
    """Average curvature in a curve"""
    # NOTE: this work slow, but direct evaluation seems
    # infeasible
    # Some hints here: https://math.stackexchange.com/questions/1954845/bezier-curvature-extrema
    t_space = np.linspace(0, 1, points_estimates)
    return max([curve.curvature(t) for t in t_space])

def _bend_extend_2_tangent(
        shift, cp, target_len, direction, 
        target_tangent_start, target_tangent_end, 
        point_estimates=50):
    """Evaluate how well curve preserves the length and tangents

        NOTE: point_estimates controls average curvature evaluation.
            The higher the number, the more stable the optimization,
            but higher computational cost
    """

    control = np.array([
        cp[0], 
        [cp[1][0] + shift[0], cp[1][1] + shift[1]], 
        [cp[2][0] + shift[2], cp[2][1] + shift[3]],
        cp[-1] + direction * shift[4]
    ])

    params = control[:, 0] + 1j*control[:, 1]
    curve_inverse = svgpath.CubicBezier(*params)

    length_diff = (curve_inverse.length() - target_len)**2  # preservation

    tan_0_diff = (abs(curve_inverse.unit_tangent(0) - target_tangent_start))**2
    tan_1_diff = (abs(curve_inverse.unit_tangent(1) - target_tangent_end))**2

    # NOTE: tried regularizing based on Y value in relative coordinates (for speed), 
    # But it doesn't produce good results
    curvature_reg = _max_curvature(curve_inverse, points_estimates=point_estimates)**2

    end_expantion_reg = 0.001*shift[-1]**2 

    return length_diff + tan_0_diff + tan_1_diff + curvature_reg + end_expantion_reg
      
def curve_match_tangents(curve, target_tan0, target_tan1, return_as_edge=False):
    """Update the curve to have the desired tangent directions at endpoints 
        while preserving curve length and overall direction

        Returns 
        * control points for the final CubicBezier curves
        * Or CurveEdge instance, if return_as_edge=True

        NOTE: Only Cubic Bezier curves are supported
    """
    if not isinstance(curve, svgpath.CubicBezier):
        raise NotImplementedError(
            f'Curve_match_tangents::Error::Only Cubic Bezier curves are supported ', 
            f'(got {type(curve)})')

    curve_cps = c_to_np(curve.bpoints())

    direction = curve_cps[-1] - curve_cps[0]
    direction /= np.linalg.norm(direction)

    target_tan0 = target_tan0 / np.linalg.norm(target_tan0)
    target_tan1 = target_tan1 / np.linalg.norm(target_tan1)

    # match tangents with the requested ones while preserving length
    out = minimize(
        _bend_extend_2_tangent, # with tangent matching
        [0, 0, 0, 0, 0], 
        args=(
            curve_cps, 
            curve.length(),
            direction,
            list_to_c(target_tan0),  
            list_to_c(target_tan1), 
            70   # NOTE: Low values cause instable resutls
        ),
        method='L-BFGS-B',
    )
    if not out.success:
        print(f'Curve_match_tangents::WARNING::optimization not successfull')
        if flags.VERBOSE:
            print(out)

    shift = out.x

    fin_curve_cps = [
        curve_cps[0].tolist(),
        [curve_cps[1][0] + shift[0], curve_cps[1][1] + shift[1]], 
        [curve_cps[2][0] + shift[2], curve_cps[2][1] + shift[3]],
        (curve_cps[-1] + direction*shift[-1]).tolist(), 
    ]

    if return_as_edge:
        fin_inv_edge = CurveEdge(
            start=fin_curve_cps[0], 
            end=fin_curve_cps[-1], 
            control_points=fin_curve_cps[1:3],
            relative=False
        )
        return fin_inv_edge
    
    return fin_curve_cps


# ---- Utils ----

def _dist(v1, v2):
    return norm(v2-v1)
