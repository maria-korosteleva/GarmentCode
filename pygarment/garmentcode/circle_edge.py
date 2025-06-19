import numpy as np
import svgpathtools as svgpath
from numpy.linalg import norm

from pygarment.garmentcode.utils import (c_to_list, close_enough, list_to_c,
                                         vector_angle)
from pygarment.pattern.utils import rel_to_abs_2d

from .edge import Edge, EdgeSequence


class CircleEdge(Edge):
    """Curvy edge as circular arc"""

    def __init__(self, start=None, end=None, cy=None, label="") -> None:
        """
        Define a circular arc edge
        * start, end: from/to vertices that the edge connects
        * cy: third point on a circle arc (= control point).
            Expressed relatively w.r.t. distance between start and end.
            X value for control point is fixed at x=0.5 (edge center) to
            avoid ambiguity
        * label: semantic label of the edge to be writted down as a property on assembly

        NOTE: representing control point in relative coordinates
        allows preservation of curvature (arc angle, relative radius
        w.r.t. straight edge length)
        When distance between vertices shrinks / extends

        NOTE: full circle not supported: start & end should differ
        """
        if start is None:
            start = [0, 0]
        if end is None:
            end = [1, 0]
        super().__init__(start, end, label=label)
        self.control_y = cy

    def length(self):
        """Return current length of an edge.
        Since vertices may change their locations externally, the length
        is dynamically evaluated
        """
        return self._rel_radius() * self._straight_len() * self._arc_angle()

    def __str__(self) -> str:

        points = [self.start, [0.5, self.control_y]]

        str = [f"[{p[0]:.2f}, {p[1]:.2f}]->" for p in points]
        str += [f"[{self.end[0]:.2f}, {self.end[1]:.2f}]"]

        return "Arc:" + "".join(str)

    def midpoint(self):
        """Center of the edge"""
        return rel_to_abs_2d(self.start, self.end, [0.5, self.control_y])

    # Actions
    def reverse(self):
        """Flip the direction of the edge, accounting for curvatures"""

        self.start, self.end = self.end, self.start
        self.control_y *= -1

        return self

    def reflect_features(self):
        """Reflect edge features from one side of the edge to the other"""

        self.control_y *= -1

        return self

    def _subdivide(self, fractions: list, by_length=False):
        """Add intermediate vertices to an edge,
        splitting its parametrization according to fractions
        while preserving the overall shape

        NOTE: param subdiv == length subdiv for circle arcs
        """
        # NOTE: subdivide_param() is the same as subdivide_len()
        # So parent implementation is ok
        # TODOLOW Implementation is very similar to CurveEdge param-based subdivision

        from pygarment.garmentcode.edge_factory import \
            EdgeFactory  # TODOLOW: ami - better solution?

        frac = [abs(f) for f in fractions]
        if not close_enough(fsum := sum(frac), 1, 1e-4):
            raise RuntimeError(
                f"Edge Subdivision::ERROR::fraction is incorrect. The sum {fsum} is not 1"
            )

        curve = self.as_curve()
        # Sub-curves
        covered_fr = 0
        subcurves = []
        for fr in fractions:
            subcurves.append(curve.cropped(covered_fr, covered_fr + fr))
            covered_fr += fr

        # Convert to CircleEdge objects
        subedges = EdgeSequence()
        for curve in subcurves:
            subedges.append(EdgeFactory.from_svg_curve(curve))
        # Reference the first/last vertices correctly
        subedges[0].start = self.start
        subedges[-1].end = self.end

        return subedges

    # Special tools for circle representation
    def as_curve(self):
        """Represent as svgpath Arc"""

        radius, la, sweep = self.as_radius_flag()

        return svgpath.Arc(
            list_to_c(self.start),
            list_to_c([radius, radius]),
            0,
            la,
            sweep,
            list_to_c(self.end),
        )

    def as_radius_flag(self):
        """Return circle representation as radius and arc flags"""

        return (
            self._rel_radius() * self._straight_len(),
            self._is_large_arc(),
            self.control_y < 0,
        )  # left/right orientation

    def as_radius_angle(self):
        """Return circle representation as radius and an angle"""

        return (
            self._rel_radius() * self._straight_len(),
            self._arc_angle(),
            self.control_y < 0,
        )

    def linearize(self, n_verts_inside=9):
        """Return a linear approximation of an edge using the same vertex objects
        NOTE: n_verts_inside = number of vertices (excluding the start
         and end vertices) used to create a linearization of the edge
        """
        n = n_verts_inside + 1
        tvals = np.linspace(0, 1, n, endpoint=False)[1:]

        curve = self.as_curve()
        edge_verts = [c_to_list(curve.point(t)) for t in tvals]
        seq = self.to_edge_sequence(edge_verts)

        return seq

    # NOTE: The following values are calculated at runtime to allow
    # changes to control point after the edge definition
    def _rel_radius(self, abs_radius=None):
        """Eval relative radius (w.r.t. straight distance) from 3-point
        representation"""

        if abs_radius:
            return abs_radius / self._straight_len()

        # Using the formula for radius of circumscribed circle
        # https://en.wikipedia.org/wiki/Circumscribed_circle#Other_properties

        # triangle sides, assuming the begginning and end of an edge are at
        # (0, 0) and (1, 0)
        # accordingly
        a = 1
        b = norm([0.5, self.control_y])
        c = norm([0.5 - 1, self.control_y])
        p = (a + b + c) / 2  # semiperimeter

        rad = a * b * c / np.sqrt(p * (p - a) * (p - b) * (p - c)) / 4

        return rad

    def _arc_angle(self):
        """Eval arc angle from control point"""
        rel_rad = self._rel_radius()

        # NOTE: Bound the sin to avoid out of bounds errors
        # due to floating point error accumulation
        arc = 2 * np.arcsin(min(max(1 / rel_rad / 2, -1.0), 1.0))

        if self._is_large_arc():
            arc = 2 * np.pi - arc

        return arc

    def _is_large_arc(self):
        """Indicate if the arc sweeps the large or small angle"""
        return abs(self.control_y) > self._rel_radius()

    def assembly(self):
        """Returns the dict-based representation of edges,
        compatible with core -> BasePattern JSON (dict)
        """
        ends, props = super().assembly()

        # NOTE: arc representation is the same as in SVG
        rad, large_arc, right = self.as_radius_flag()
        props["curvature"] = {
            "type": "circle",
            "params": [rad, int(large_arc), int(right)],
        }
        return ends, props


class CircleEdgeFactory:
    @staticmethod
    def from_points_angle(start, end, arc_angle, right=True):
        """Construct circle arc from two fixed points and an angle

        arc_angle:

        NOTE: Might fail on angles close to 2pi
        """
        # Big or small arc
        if arc_angle > np.pi:
            arc_angle = 2 * np.pi - arc_angle
            to_sum = True
        else:
            to_sum = False

        radius = 1 / np.sin(arc_angle / 2) / 2
        h = 1 / np.tan(arc_angle / 2) / 2

        control_y = radius + h if to_sum else radius - h  # relative control point
        control_y *= -1 if right else 1

        return CircleEdge(start, end, cy=control_y)

    @staticmethod
    def from_points_radius(start, end, radius, large_arc=False, right=True):
        """Construct circle arc relative representation
        from two fixed points and an (absolute) radius
        """
        # Find circle center
        str_dist = norm(np.asarray(end) - np.asarray(start))

        # NOTE: close enough values may give negative
        # value under sqrt due to numerical errors
        if close_enough(radius**2, str_dist**2 / 4, 1e-3):
            center_r = 0.0
        else:
            center_r = np.sqrt(radius**2 - str_dist**2 / 4)

        # Find the absolute value of Y
        control_y = radius + center_r if large_arc else radius - center_r

        # Convert to relative
        control_y = control_y / str_dist

        # Flip sight according to "right" parameter
        control_y *= -1 if right else 1

        return CircleEdge(start, end, cy=control_y)

    @staticmethod
    def from_rad_length(rad, length, right=True, start=None):
        """NOTE: if start vertex is not provided, both vertices will be created
        to match desired radius and length
        """
        max_len = 2 * np.pi * rad

        if length > max_len:
            raise ValueError(
                f"CircleEdge::ERROR::Incorrect length for specified radius"
            )

        large_arc = length > max_len / 2
        if large_arc:
            length = max_len - length

        w_half = rad * np.sin(length / rad / 2)

        edge = CircleEdgeFactory.from_points_radius(
            [-w_half, 0], [w_half, 0], radius=rad, large_arc=large_arc, right=right
        )

        if start:
            edge.snap_to(start)
            edge.start = start

        return edge

    @staticmethod
    def from_three_points(start, end, point_on_arc, relative=False):
        """Create a circle arc from 3 points (start, end and any point on an arc)

        NOTE: Control point specified in the same coord system as start and end
        NOTE: points should not be on the same line
        """
        if relative:
            point_on_arc = rel_to_abs_2d(start, end, point_on_arc)

        nstart, nend, npoint_on_arc = (
            np.asarray(start),
            np.asarray(end),
            np.asarray(point_on_arc),
        )

        # https://stackoverflow.com/a/28910804
        # Using complex numbers to calculate the center & radius
        x, y, z = list_to_c([start, point_on_arc, end])
        w = z - x
        w /= y - x
        c = (x - y) * (w - abs(w) ** 2) / 2j / w.imag - x
        # NOTE center = [c.real, c.imag]
        rad = abs(c + x)

        # Large/small arc
        mid_dist = norm(npoint_on_arc - ((nstart + nend) / 2))

        # Orientation
        angle = vector_angle(npoint_on_arc - nstart, nend - nstart)  # +/-

        return CircleEdgeFactory.from_points_radius(
            start, end, radius=rad, large_arc=mid_dist > rad, right=angle > 0
        )
