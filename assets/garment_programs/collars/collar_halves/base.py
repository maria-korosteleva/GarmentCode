import numpy as np

import pygarment as pyg
from assets.garment_programs.collars.collar_halves import factory

# # ------ Collar shapes withough extra panels ------


@factory.register_builder("VNeckHalf")
def VNeckHalf(depth: float, width: float, **kwargs):
    """Simple VNeck design"""

    edges = pyg.EdgeSequence(pyg.Edge([0, 0], [width / 2, -depth]))
    return edges


@factory.register_builder("SquareNeckHalf")
def SquareNeckHalf(depth: float, width: float, **kwargs):
    """Square design"""

    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    return edges


@factory.register_builder("TrapezoidNeckHalf")
def TrapezoidNeckHalf(
    depth: float, width: float, angle: float = 90.0, verbose: bool = True, **kwargs
):
    """Trapesoid neck design"""

    # Special case when angle = 180 (sin = 0)
    if pyg.utils.close_enough(angle, 180, tol=1) or pyg.utils.close_enough(
        angle, 0, tol=1
    ):
        # degrades into VNeck
        return VNeckHalf(depth, width)

    rad_angle = np.deg2rad(angle)

    bottom_x = -depth * np.cos(rad_angle) / np.sin(rad_angle)
    if (
        bottom_x > width / 2
    ):  # Invalid angle/depth/width combination resulted in invalid shape
        if verbose:
            print(
                "TrapezoidNeckHalf::WARNING::Parameters are invalid and create overlap: "
                f"{bottom_x} > {width / 2}. "
                "The collar is reverted to VNeck"
            )

        return VNeckHalf(depth, width)

    edges = pyg.EdgeSeqFactory.from_verts(
        [0, 0], [bottom_x, -depth], [width / 2, -depth]
    )
    return edges


@factory.register_builder("CurvyNeckHalf")
def CurvyNeckHalf(depth: float, width: float, flip: float = False, **kwargs):
    """Testing Curvy Collar design"""

    sign = -1 if flip else 1
    edges = pyg.EdgeSequence(
        pyg.CurveEdge(
            [0, 0], [width / 2, -depth], [[0.4, sign * 0.3], [0.8, sign * -0.3]]
        )
    )

    return edges


@factory.register_builder("CircleArcNeckHalf")
def CircleArcNeckHalf(
    depth: float, width: float, angle: float = 90.0, flip: bool = False, **kwargs
):
    """Collar with a side represented by a circle arc"""
    # 1/4 of a circle
    edges = pyg.EdgeSequence(
        pyg.CircleEdgeFactory.from_points_angle(
            [0, 0], [width / 2, -depth], arc_angle=np.deg2rad(angle), right=(not flip)
        )
    )

    return edges


@factory.register_builder("CircleNeckHalf")
def CircleNeckHalf(depth: float, width: float, **kwargs):
    """Collar that forms a perfect circle arc when halfs are stitched"""

    # Take a full desired arc and half it!
    circle = pyg.CircleEdgeFactory.from_three_points(
        [0, 0], [width, 0], [width / 2, -depth]
    )
    subdiv = circle.subdivide_len([0.5, 0.5])
    return pyg.EdgeSequence(subdiv[0])


@factory.register_builder("Bezier2NeckHalf")
def Bezier2NeckHalf(
    depth: float,
    width: float,
    flip: bool = False,
    x: float = 0.5,
    y: float = 0.3,
    **kwargs,
):
    """2d degree Bezier curve as neckline"""

    sign = 1 if flip else -1
    edges = pyg.EdgeSequence(
        pyg.CurveEdge([0, 0], [width / 2, -depth], [[x, sign * y]])
    )

    return edges
