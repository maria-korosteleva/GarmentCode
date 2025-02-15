from copy import deepcopy

import numpy as np
import pygarment as pyg
from assets.garment_programs.sleeves.armhole_shapes import factory


# ------  Armhole shapes ------
@factory.register_builder("ArmholeSquare")
def ArmholeSquare(
    incl: float, width: float, angle: float, invert: bool = True, **kwargs
):
    """Simple square armhole cut-out
    Not recommended to use for sleeves, stitching in 3D might be hard

    if angle is provided, it also calculated the shape of the sleeve interface to attach

    returns edge sequence and part to be preserved  inverted
    """

    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [incl, 0], [incl, width])
    if not invert:
        return edges, None

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyg.EdgeSeqFactory.from_verts(
        [incl + l * sina, -l * cosa], [incl, 0], [incl, width]
    )

    # TODOLOW Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle)

    return edges, sleeve_edges


@factory.register_builder("ArmholeAngle")
def ArmholeAngle(
    incl: float,
    width: float,
    angle: float,
    incl_coeff: float = 0.2,
    w_coeff: float = 0.2,
    invert: bool = True,
    **kwargs
):
    """Piece-wise smooth armhole shape"""
    diff_incl = incl * (1 - incl_coeff)
    edges = pyg.EdgeSeqFactory.from_verts(
        [0, 0], [diff_incl, w_coeff * width], [incl, width]
    )
    if not invert:
        return edges, None

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyg.EdgeSeqFactory.from_verts(
        [diff_incl + l * sina, w_coeff * width - l * cosa],
        [diff_incl, w_coeff * width],
        [incl, width],
    )
    # TODOLOW Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle)

    return edges, sleeve_edges


@factory.register_builder("ArmholeCurve")
def ArmholeCurve(
    incl: float,
    width: float,
    angle: float,
    bottom_angle_mix: float = 0,
    invert: bool = True,
    verbose: bool = False,
    **kwargs
):
    """Classic sleeve opening on Cubic Bezier curves"""
    # Curvature as parameters?
    cps = [[0.5, 0.2], [0.8, 0.35]]
    edge = pyg.CurveEdge([incl, width], [0, 0], cps)
    edge_as_seq = pyg.EdgeSequence(edge.reverse())

    if not invert:
        return edge_as_seq, None

    # Initialize inverse (initial guess)
    # Agle == 0
    down_direction = np.array([0, -1])  # Full opening is vertically aligned
    inv_cps = deepcopy(cps)
    inv_cps[-1][1] *= -1  # Invert the last
    inv_edge = pyg.CurveEdge(
        start=[incl, width],
        end=(np.array([incl, width]) + down_direction * edge._straight_len()).tolist(),
        control_points=inv_cps,
    )

    # Rotate by desired angle (usually desired sleeve rest angle)
    inv_edge.rotate(angle=-angle)

    # Optimize the inverse shape to be nice
    shortcut = inv_edge.shortcut()
    rotated_direction = shortcut[-1] - shortcut[0]
    rotated_direction /= np.linalg.norm(rotated_direction)
    left_direction = np.array([-1, 0])
    mix_factor = bottom_angle_mix

    dir = (1 - mix_factor) * rotated_direction + (
        mix_factor * down_direction
        if mix_factor > 0
        else (-mix_factor * left_direction)
    )

    # TODOLOW Remember relative curvature results and reuse them? (speed)
    fin_inv_edge = pyg.ops.curve_match_tangents(
        inv_edge.as_curve(),
        down_direction,  # Full opening is vertically aligned
        dir,
        target_len=edge.length(),
        return_as_edge=True,
        verbose=verbose,
    )

    return edge_as_seq, pyg.EdgeSequence(fin_inv_edge.reverse())
