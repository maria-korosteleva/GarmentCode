from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm
import svgpathtools as svgpath  # https://github.com/mathandy/svgpathtools

# Custom
from .generic_utils import vector_angle, R2D, close_enough, c_to_list, list_to_c
from .flags import VERBOSE

class Edge():
    """Edge -- an individual segement of a panel border connecting two panel vertices, 
     the basic building block of panels

    Edges are defined on 2D coordinate system with Start vertex as an origin and (End-Start) as Ox axis
    """

    def __init__(self, start=[0,0], end=[0,0]) -> None:
        """ Simple edge inititalization.
        Parameters: 
            * start, end: from/to vertcies that the edge connectes, describing the _interface_ of an edge

            # TODOLOW Add support for fold schemes to allow guided folds at the edge (e.g. pleats)
        """

        assert not all(close_enough(s, e) for s, e in zip(start, end)), 'Start and end of an edge should differ'

        self.start = start  # NOTE: careful with references to vertex objects
        self.end = end

        # ID w.r.t. other edges in a super-panel
        # Filled out at the panel assembly time
        self.geometric_id = 0

    # Info
    def length(self):
        """Return current length of an edge.
            Since vertices may change their locations externally, the length is dynamically evaluated
        """
        return self._straight_len()

    def _straight_len(self):
        """Length of the edge ignoring the curvature"""
        return norm(np.asarray(self.end) - np.asarray(self.start))

    def __eq__(self, __o: object, tol=1e-2) -> bool:
        """Special implementation of comparison: same edges == edges can be connected by flat stitch
            Edges are the same if their length is the same (if their flattened representation is the same)
                => vertices do not have to be on the same locations

            NOTE: The edges may not have the same curvature and still be considered equal ("connectible")
        """

        if not isinstance(__o, Edge):
            return False

        # Base length is the same
        if close_enough(self.length(), __o.length(), tol=tol):
            return False

        return True

    def __str__(self) -> str:
        return f'Straight:[{self.start[0]:.2f}, {self.start[1]:.2f}]->[{self.end[0]:.2f}, {self.end[1]:.2f}]'

    def __repr__(self) -> str:
        """ 'Official string representation' -- for nice printing of lists of edges
        
        https://stackoverflow.com/questions/3558474/how-to-apply-str-function-when-printing-a-list-of-objects-in-python
        """
        return self.__str__()

    def midpoint(self):
        """Center of the edge"""
        return (np.array(self.start) + np.array(self.end)) / 2

    def shortcut(self):
        """Return straight shortcut for an edge, 
            as np.array
        
            For straight edges it's the same as the edge itself
        """

        return np.array([self.start, self.end])

    # Representation
    def as_curve(self):
        """As svgpath curve object"""
        # Get the nodes correcly
        nodes = np.vstack((self.start, self.end))

        params = nodes[:, 0] + 1j*nodes[:, 1]

        return svgpath.Line(*params)

    def linearize(self, n_verts_inside = 0):
        """Return a linear approximation of an edge using the same vertex objects
        
            # NOTE: for the linear edge it is an egde if n_verts_inside = 0,
            # else n_verts_inside = number of vertices (excluding the start
            and end vertices) used to create a linearization of the edge
        """

        if not n_verts_inside:
            return self
        else:
            n = n_verts_inside + 1
            tvals = np.linspace(0, 1, n, endpoint=False)[1:]

            curve = self.as_curve()
            edge_verts = [c_to_list(curve.point(t)) for t in tvals]
            seq = self.to_edge_sequence(edge_verts)

            return seq

    def to_edge_sequence(self, edge_verts):
        """
        Returns the edge as a sequence of STRAIGHT edges based on points sampled on the edge
        between self.start and self.end (edge_verts).
        """
        seq = EdgeSequence(Edge(self.start, edge_verts[0]))
        for i in range(1, len(edge_verts)):
            seq.append(Edge(seq[-1].end, edge_verts[i]))
        seq.append(Edge(seq[-1].end, self.end))

        return seq

    # Support for relative coordinate system
    def _rel_to_abs_2d(self, point):
        """Convert coordinates expressed relative to an edge into absolute """
        start, end = np.array(self.start), np.array(self.end)
        edge = end - start
        edge_perp = np.array([-edge[1], edge[0]])

        conv_start = self.start + point[0] * edge
        conv_point = conv_start + point[1] * edge_perp
        
        return conv_point

    def _abs_to_rel_2d(self, point):
        """Convert control points coordinates from absolute to relative"""
        start, end = np.array(self.start), np.array(self.end)
        edge = end - start
        edge_len = norm(edge)

        point_vec = np.asarray(point) - start

        converted = [None, None]
        # X
        # project control_vec on edge by dot product properties
        projected_len = edge.dot(point_vec) / edge_len 
        converted[0] = projected_len / edge_len
        # Y
        control_projected = edge * converted[0]
        vert_comp = point_vec - control_projected  
        converted[1] = norm(vert_comp) / edge_len

        # Distinguish left&right curvature
        converted[1] *= -np.sign(np.cross(point_vec, edge)) 
        
        return np.asarray(converted)

    # Actions
    def reverse(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start

        return self
    
    def reflect_features(self):
        """Reflect edge fetures from one side of the edge to the other"""
        # Nothing to do for straight edge
        return self

    def snap_to(self, new_start=[0, 0]):
        """Translate the edge vertices s.t. the start is at new_start
        """
        self.end[0] = self.end[0] - self.start[0] + new_start[0]
        self.end[1] = self.end[1] - self.start[1] + new_start[1]

        self.start[:] = new_start
        return self

    def rotate(self, angle):
        """Rotate edge by angle in place, using first point as a reference

        Parameters: 
            angle -- desired rotation angle in radians (!)
        """
        curr_start = copy(self.start)
        
        # set the start point to zero
        self.snap_to([0, 0])
        self.end[:] = np.matmul(R2D(angle), self.end)
        
        # recover the original location
        self.snap_to(curr_start)

        return self
        
    def subdivide_len(self, fractions: list, connect_internal_verts=True):
        """Add intermediate vertices to an edge, 
            splitting it's length according to fractions
            while preserving the overall shape

            * merge_internal -- if False, the newly inserted vertices would be defined
                as independent objects for each edge. If True, vertex objects will be shared
        """
        # Parametrized by length
        new_edges = self._subdivide(fractions, by_length=True)

        if connect_internal_verts:
            self._merge_subdiv_vertices(new_edges)
        
        return new_edges
    
    def subdivide_param(self, fractions: list, connect_internal_verts=True):
        """Add intermediate vertices to an edge, 
            splitting its curve parametrization according to fractions
            while preserving the overall shape

            NOTE: for line, it's the same as subdivision by length
        """
        
        new_edges = self._subdivide(fractions, by_length=False)

        if connect_internal_verts:
            self._merge_subdiv_vertices(new_edges)
        
        return new_edges


    # DRAFT This will not work for curves though
    #  def subdivide_point(self, point:list):
    #     """Subdivide the edge into two at the given point
    #     """
    #     # NOTE: works for children classes as well
    #     curve = self.as_curve()
    #     param = curve.point_to_t(list_to_c(point))

    #     curve = svgpath.CubicBezier(0+0j, 0.3+0.5j, 0.6+0.2j, 1+0j)

    #     return self._subdivide([param, 1-param], False)

    def _subdivide(self, fractions: list, by_length=True):
        """Subdivide edge by length or curve parametrization

            NOTE: equivalent for straight lines
        """

        frac = [abs(f) for f in fractions]
        if not close_enough(fsum:=sum(frac), 1, 1e-4):
            raise RuntimeError(f'Edge Subdivision::Error::fraction is incorrect. The sum {fsum} is not 1')

        vec = np.asarray(self.end) - np.asarray(self.start)
        verts = [self.start]
        seq = EdgeSequence()
        for i in range(len(frac) - 1):
            verts.append(
                [verts[-1][0] + frac[i]*vec[0],
                verts[-1][1] + frac[i]*vec[1]]
            )
            seq.append(Edge(verts[-2], verts[-1]))
        verts.append(self.end)
        seq.append(Edge(verts[-2], verts[-1]))
        
        return seq

    def _merge_subdiv_vertices(self, subdivision):
        """Merge the vertices from cosecutive edges in the given edge subdivision"""

        for i in range(1, len(subdivision)):
            subdivision[i].start = subdivision[i-1].end
        return subdivision

    @staticmethod
    def from_svg_curve(seg):
        """Create Edge object from svgpath object"""

        start, end = c_to_list(seg.start), c_to_list(seg.end)
        if isinstance(seg, svgpath.Line):
            return Edge(start, end)
        if isinstance(seg, svgpath.Arc):
            # NOTE: assuming circular arc (same radius in both directoins)
            radius = seg.radius.real
            return CircleEdge.from_points_radius(
                start, end, radius, seg.large_arc, seg.sweep
            )

        # Only Bezier left
        if isinstance(seg, svgpath.QuadraticBezier):
            cp = [c_to_list(seg.control)]
        elif isinstance(seg, svgpath.CubicBezier):
            cp = [c_to_list(seg.control1), c_to_list(seg.control2)]
        else:
            raise NotImplementedError(f'CurveEdge::Error::Incorrect curve type supplied {seg.type}')
        
        return CurveEdge(start, end, cp, relative=False)

    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges, 
            compatible with core -> BasePattern JSON (dict) 
        """

        return [self.start, self.end], {"endpoints": [0, 1]}


class CircleEdge(Edge):
    """Curvy edge as circular arc"""

    def __init__(self, start=[0, 0], end=[0, 0], cy=None) -> None:
        """
            Define a circular arc edge
            * start, end: from/to vertcies that the edge connectes
            * cy: third point on a circle arc (= control point). 
                Expressed relatively w.r.t. distance between start and end. 
                X value for control point is fixed at x=0.5 (edge center) to avoid ambiguity
            
            NOTE: represening control point in relative coordinates
            allows preservation of curvature (arc angle, relative raidus w.r.t. straight edge length)
            When distance between vertices shrinks / extends

            NOTE: full circle not supported: start & end should differ
        """
        super().__init__(start, end)
        
        self.control_y = cy

    def length(self):
        """Return current length of an edge.
            Since vertices may change their locations externally, the length is dynamically evaluated
        """
        return self._rel_radius() * self._straight_len() * self._arc_angle()

    def __str__(self) -> str:

        points = [self.start, [0.5, self.control_y]]

        str = [f'[{p[0]:.2f}, {p[1]:.2f}]->' for p in points]
        str += [f'[{self.end[0]:.2f}, {self.end[1]:.2f}]']

        return 'Arc:' + ''.join(str)
    
    def midpoint(self):
        """Center of the edge"""
        return self._rel_to_abs_2d([0.5, self.control_y])

    # Actions
    def reverse(self):
        """Flip the direction of the edge, accounting for curvatures"""

        self.start, self.end = self.end, self.start
        self.control_y *= -1

        return self
    
    def reflect_features(self):
        """Reflect edge fetures from one side of the edge to the other"""

        self.control_y *= -1

        return self

    def _subdivide(self, fractions: list, by_length=False):
        """Add intermediate vertices to an edge, 
            splitting it's parametrization according to fractions
            while preserving the overall shape
        
            NOTE: param subdiv == length subdiv for circle arcs
        """
        # NOTE: subdivide_param() is the same as subdivide_len()
        # So parent implementation is ok
        # TODOLOW Implementation is very similar to CurveEdge param-based subdivision
        frac = [abs(f) for f in fractions]
        if not close_enough(fsum:=sum(frac), 1, 1e-4):
            raise RuntimeError(f'Edge Subdivision::Error::fraction is incorrect. The sum {fsum} is not 1')

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
            subedges.append(Edge.from_svg_curve(curve))
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
            list_to_c([radius, radius]), 0, la, sweep,
            list_to_c(self.end)
        )
  
    def as_radius_flag(self):
        """Return circle representation as radius and arc flags"""

        return (self._rel_radius() * self._straight_len(), 
                self._is_large_arc(),
                self.control_y < 0)   # left/right orientation 
  
    def as_radius_angle(self):
        """Return circle representation as radius and an angle"""

        return (
            self._rel_radius() * self._straight_len(),
            self._arc_angle(),
            self.control_y < 0
        )

    def linearize(self, n_verts_inside = 9):
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
        """Eval relative radius (w.r.t. straight distance) from 3-point representation"""

        if abs_radius: 
            return abs_radius / self._straight_len()

        # Using the formula for radius of circumscribed circle
        # https://en.wikipedia.org/wiki/Circumscribed_circle#Other_properties

        # triangle sides, assuming the begginning and end of an edge are at (0, 0) and (1, 0)
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
        arc = 2 * np.arcsin(1 / rel_rad / 2)

        if self._is_large_arc():
            arc = 2 * np.pi - arc
        
        return arc
    
    def _is_large_arc(self):
        """Indicate if the arc sweeps the large or small angle"""
        return abs(self.control_y) > self._rel_radius()
    
    # Factories
    @staticmethod
    def from_points_angle(start, end, arc_angle, right=True):
        """Construct circle arc from two fixed points and an angle
        
            arc_angle: 
            
            NOTE: Might fail on angles close to 2pi
        """
        # Big or small arc
        if arc_angle > np.pi:
            arc_angle = 2*np.pi - arc_angle
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
            raise ValueError(f'CircleEdge::ERROR::Incorrect length for specified radius')

        large_arc = length > max_len / 2
        if large_arc:
            length = max_len - length

        w_half = rad * np.sin(length / rad / 2)

        edge = CircleEdge.from_points_radius(
            [-w_half, 0], [w_half, 0], 
            radius=rad, 
            large_arc=large_arc,
            right=right
        )

        if start: 
            edge.snap_to(start)
            edge.start = start

        return edge


    @staticmethod
    def from_three_points(start, end, point_on_arc):
        """Create a circle arc from 3 points (start, end and any point on an arc)
        
            NOTE: Control point specified in the same coord system as start and end
            NOTE: points should not be on the same line
        """

        nstart, nend, npoint_on_arc = np.asarray(start), np.asarray(end), np.asarray(point_on_arc)

        # https://stackoverflow.com/a/28910804
        # Using complex numbers to calculate the center & radius
        x, y, z = list_to_c([start, point_on_arc, end]) 
        w = z - x
        w /= y - x
        c = (x - y)*(w - abs(w)**2)/2j/w.imag - x
        # NOTE center = [c.real, c.imag]
        rad = abs(c + x)

        # Large/small arc
        mid_dist = norm(npoint_on_arc - ((nstart + nend) / 2))

        # Orientation
        angle = vector_angle(npoint_on_arc - nstart, nend - nstart)  # +/-

        return CircleEdge.from_points_radius(
            start, end, radius=rad, 
            large_arc=mid_dist > rad, right=angle > 0) 

    # Finally
    def assembly(self):
        """Returns the dict-based representation of edges, 
            compatible with core -> BasePattern JSON (dict) 
        """

        # TODOLOW Try the 3-point representation in JSON? Might be more compact + more continious
        # How much human readible this one should be?
        # Even one number (Y axis) could be enough 

        rad, large_arc, right = self.as_radius_flag()
        return (
            [self.start, self.end], 
            {
                "endpoints": [0, 1], 
                "curvature": {
                    "type": 'circle',
                    "params": [rad, int(large_arc), int(right)]
                }
            })


class CurveEdge(Edge):
    """Curvy edge as Besier curve / B-spline"""

    def __init__(self, start=[0, 0], end=[0, 0], control_points=[], relative=True) -> None:
        """Define a Besier curve edge
            * start, end: from/to vertcies that the edge connectes
            * control_points: coordinated of Bezier control points.
                Specification of One control point creates the Quadratic Bezier, 
                Specification of 2 control points creates Cubic Bezier. 
                Other degrees are not supported.

            * relative: specify whether the control point coordinated are given 
            relative to the edge length (True) or in 2D coordinate system of a panel (False)

        """
        super().__init__(start, end)

        # FIXME Self-intersections tests

        self.control_points = control_points

        if len(self.control_points) > 2:
            raise NotImplementedError(f'{self.__class__.__name__}::Error::Up to 2 control points (cubic Bezier) are supported')

        # Storing control points as relative since it preserves overall curve shape during
        # edge extention/contration
        if not relative:
            self.control_points = [self._abs_to_rel_2d(c).tolist() for c in self.control_points]

    def length(self):
        """Length of Bezier curve edge"""
        curve = self.as_curve()
        
        return curve.length()

    def __str__(self) -> str:

        points = [self.start] + self.control_points

        str = [f'[{p[0]:.2f}, {p[1]:.2f}]->' for p in points]
        str += [f'[{self.end[0]:.2f}, {self.end[1]:.2f}]']

        return 'Curve:' + ''.join(str)
    
    def midpoint(self):
        """Center of the edge"""
        curve = self.as_curve()

        t_mid = curve.ilength(curve.length()/2)
        return c_to_list(curve.point(t_mid))
    
    def _subdivide(self, fractions: list, by_length=False):
        """Add intermediate vertices to an edge, 
            splitting its curve parametrization or overall length according to 
            fractions while preserving the overall shape
        """
        curve = self.as_curve()

        # Sub-curves
        covered_fr, prev_t = 0, 0
        clen = curve.length()
        subcurves = []
        for fr in fractions:
            covered_fr += fr
            if by_length:
                next_t = curve.ilength(clen * covered_fr)
                subcurves.append(curve.cropped(prev_t, next_t))
                prev_t = next_t
            else:
                subcurves.append(curve.cropped(covered_fr - fr, covered_fr))

        # Convert to CurveEdge objects
        subedges = EdgeSequence()
        for curve in subcurves:
            subedges.append(Edge.from_svg_curve(curve))
        # Reference the first/last vertices correctly
        subedges[0].start = self.start
        subedges[-1].end = self.end

        return subedges

    # Actions
    def reverse(self):
        """Flip the direction of the edge, accounting for curvatures"""

        self.start, self.end = self.end, self.start

        # change order of control points
        if len(self.control_points) == 2:
            self.control_points[0], self.control_points[1] = self.control_points[1], self.control_points[0]

        # Update coordinates
        for p in self.control_points:
            p[0], p[1] = 1 - p[0], -p[1]

        return self
    
    def reflect_features(self):
        """Reflect edge fetures from one side of the edge to the other"""

        for p in self.control_points:
            p[1] = -p[1]

        return self
    
    def as_curve(self, absolute=True):
        """As svgpath curve object

            Converting on the fly as exact vertex location might have been updated since
            the creation of the edge
        """
        # Get the nodes correcly
        if absolute:
            cp = [self._rel_to_abs_2d(c) for c in self.control_points]
            nodes = np.vstack((self.start, cp, self.end))
        else:
            cp = self.control_points
            nodes = np.vstack(([0, 0], cp, [1, 0]))
        
        params = nodes[:, 0] + 1j*nodes[:, 1]

        return svgpath.QuadraticBezier(*params) if len(cp) < 2 else svgpath.CubicBezier(*params)

    def linearize(self, n_verts_inside = 9):
        """Return a linear approximation of an edge using the same vertex objects
           NOTE: n_verts_inside = number of vertices (excluding the start
           and end vertices) used to create a linearization of the edge

        """
        # TODO Use linearization for more correct 3D visualization 
        # and self-intersection estimation

        n = n_verts_inside + 1
        tvals_init = np.linspace(0, 1, n, endpoint=False)[1:]

        curve = self.as_curve(absolute=False)
        curve_lengths = tvals_init * curve.length()
        tvals = [curve.ilength(c_len) for c_len in curve_lengths]

        edge_verts = [self._rel_to_abs_2d(c_to_list(curve.point(t))) for t in tvals]
        seq = self.to_edge_sequence(edge_verts)

        return seq

    def _extreme_points(self):
        """Return extreme points (on Y) of the current edge
            NOTE: this does NOT include the border vertices of an edge
        """

        # Variation of https://github.com/mathandy/svgpathtools/blob/5c73056420386753890712170da602493aad1860/svgpathtools/bezier.py#L197
        curve = self.as_curve(absolute=False)   # relative coords to find real extremizers
        poly = svgpath.bezier2polynomial(curve, return_poly1d=True)
        y = svgpath.imag(poly)
        dy = y.deriv()
        y_extremizers = svgpath.polyroots(dy, realroots=True,
                                          condition=lambda r: 0 < r < 1)

        extreme_points = np.array(
            [self._rel_to_abs_2d(c_to_list(curve.point(t))) for t in y_extremizers]
        )

        return extreme_points

    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges, 
            compatible with core -> BasePattern JSON (dict) 
        """

        return (
            [self.start, self.end], 
            {
                "endpoints": [0, 1], 
                "curvature": {
                    "type": 'quadratic' if len(self.control_points) == 1 else 'cubic',
                    "params": self.control_points
                }
            })

    
class EdgeSequence():
    """Represents a sequence of (possibly chained) edges (e.g. every next edge starts from the same vertex that the previous edge ends with
        and allows building some typical edge sequences
    """
    def __init__(self, *args) -> None:
        self.edges = []
        for arg in args:
            self.append(arg)

    @staticmethod
    def from_svg_path(path:svgpath.Path, dist_tol=0.05):
        """Convert SVG path given as svgpathtool Path object to an EdgeSequence
            
        * dist_tol: tolerance for vertex closeness to be considered the same vertex
            NOTE: Assumes that the path can be chained
        """
        # Convert as is
        edges = []
        for seg in path._segments:
            # skip segments of length zero
            if close_enough(seg.length(), tol=dist_tol):
                if VERBOSE:
                    print('Skipped: ', seg)  
                continue
            edges.append(Edge.from_svg_curve(seg))

        # Chain the edges
        if len(edges) > 1: 
            for i in range(1, len(edges)):

                if not all(close_enough(s, e, tol=dist_tol) for s, e in zip(edges[i].start, edges[i - 1].end)):
                    raise ValueError('EdgeSequence::from_svg_path::input path is not chained')

                edges[i].start = edges[i - 1].end


        return EdgeSequence(*edges)

    # ANCHOR Properties
    def __getitem__(self, i):
        if isinstance(i, slice):
            # return an EdgeSequence object for slices
            e_slice = self.edges[i]
            return EdgeSequence(e_slice)
        else:
            return self.edges[i]

    def index(self, elem):
        # Find the same object (by reference) 
        # list.index() is doing something different..
        # https://stackoverflow.com/a/47057419
        return next(i for i, e in enumerate(self.edges) if elem is e)

    def __len__(self):
        """Number of edges in the sequence"""
        return len(self.edges)

    def __contains__(self, item):
        # check presence by comparing references
        return any([item is e for e in self.edges])

    def __str__(self) -> str:
        return 'EdgeSeq: ' + str(self.edges)
    
    def __repr__(self) -> str:
        return self.__str__()

    def length(self):
        """Total length of edges"""
        return sum([e.length() for e in self.edges])

    def isLoop(self):
        return self.edges[0].start is self.edges[-1].end and len(self) > 1

    def isChained(self):
        """Does the sequence of edges represent correct chain?"""
        if len(self) < 2:
            return False

        for i in range(1, len(self.edges)):
            if self.edges[i].start is not self.edges[i-1].end:
                if VERBOSE:
                    # This should be helpful to catch bugs
                    print(f'{self.__class__.__name__}::Warning!::Edge sequence is not properly chained')
                return False
        return True

    def fractions(self) -> list:
        """Fractions of the lengths of each edge in sequence w.r.t. 
            the whole sequence
        """
        total_len = sum([e.length() for e in self.edges])

        return [e.length() / total_len for e in self.edges]

    def lengths(self) -> list:
        """Lengths of individual edges in the sequence"""
        return [e.length() for e in self.edges]

    def verts(self):
        """Return all vertex objects"""
        verts = [self.edges[0].start]
        for e in self.edges:
            if e.start is not verts[-1]:  # avoid adding the vertices of chained edges twice
                verts.append(e.start)
            verts.append(e.end)
        if verts[0] is verts[-1]:  # don't double count the loop origin
            verts.pop(-1)
        return verts

    def shortcut(self):
        """Opening of an edge sequence as a vector
        
            # NOTE May not reflect true shortcut if the egdes were flipped but the order remained
        """
        return np.array([self[0].start, self[-1].end]) 

    def bbox(self):
        """
        This function evaluates the 2D bounding box of the current panel and returns the panel vertices which are
        located on the bounding box (b_points).
        Output:
            * bbox (list): [min_x, max_x, min_y, max_y] of verts_2d
            * b_points (list): list of 2D vertices representing the b_points, i.e.,
              the vertices of verts_2d located on the bounding box
        """
        # Take linear version of the edges
        # To correctly process edges with extreme curvatures

        lin_edges = EdgeSequence([e.linearize() for e in self.edges])
        verts_2d = np.asarray(lin_edges.verts())
        mi = verts_2d.min(axis=0)
        ma = verts_2d.max(axis=0)
        xs = [mi[0],ma[0]]
        ys = [mi[1],ma[1]]
        #return points on bounding box
        b_points = []
        for v in verts_2d:
            if v[0] in xs or v[1] in ys:
                b_points.append(v)
        if len(b_points) == 2:
            if not any(np.array_equal(arr, mi) for arr in b_points):
                b_points = [b_points[0], mi, b_points[1]]
            else:
                p = [mi[0],ma[1]]
                b_points = [b_points[0],p,b_points[1]]

        bbox = [mi[0], ma[0], mi[1], ma[1]]

        return bbox, b_points

    # ANCHOR Modifiers
    # All modifiers return self object to allow chaining
    # Wrappers around python's list
    def append(self, item):
        if isinstance(item, Edge):
            self.edges.append(item)
        elif isinstance(item, list):  # List of edge / EdgeSeq objects
            for e in item:
                self.append(e)
        elif isinstance(item, EdgeSequence):
            self.edges += item.edges
        else:
            raise ValueError(f'{self.__class__.__name__}::Error::Trying to add object of incompatible type {type(item)}')
        return self

    def insert(self, i, item):
        if isinstance(item, Edge):
            self.edges.insert(i, item)
        elif isinstance(item, list) or isinstance(item, EdgeSequence):
            for j in range(len(item)):
                self.edges.insert(i + j, item[j])
        else:
            raise NotImplementedError(f'{self.__class__.__name__}::Error::incerting object of {type(item)} not suported (yet)')
        return self
    
    def pop(self, i):
        if isinstance(i, Edge):
            i = self.index(i)
        self.edges.pop(i)
        return self

    def substitute(self, orig, new):
        """Remove orign item from the list and place seq into it's place
            orig can be either an id of an item to remove 
            or an instance of Edge that exists in the current sequence
        """
        if isinstance(orig, Edge):
            orig = self.index(orig)
        if orig < 0: 
            orig = len(self) + orig 
        self.pop(orig)
        self.insert(orig, new)
        return self

    def reverse(self):
        """Reverse edge sequence in-place"""
        self.edges.reverse()
        for edge in self.edges:
            edge.reverse()
        return self

    # EdgeSequence-specific
    def translate_by(self, shift):
        """Translate the edge seq vertices s.t. the first vertex is at new_origin
        """
        for v in self.verts():
            v[0] += shift[0]
            v[1] += shift[1]
        return self

    def snap_to(self, new_origin=[0, 0]):
        """Translate the edge seq vertices s.t. the first vertex is at new_origin
        """
        start = copy(self[0].start)
        shift = [new_origin[0] - start[0], new_origin[1] - start[1]]
        self.translate_by(shift)

        return self

    def close_loop(self):
        """if edge loop is not closed, add and edge to close it"""
        self.isChained()  # print warning if smth is wrong
        if not self.isLoop():
            self.append(Edge(self[-1].end, self[0].start))
        return self

    def rotate(self, angle):
        """Rotate edge sequence by angle in place, using first point as a reference

        Parameters: 
            angle -- desired rotation angle in radians (!)
        """
        curr_start = copy(self[0].start)
        
        # set the start point to zero
        self.snap_to([0, 0])
        rot = R2D(angle)

        for v in self.verts():
            v[:] = np.matmul(rot, v)
        
        # recover the original location
        self.snap_to(curr_start)

        return self

    def extend(self, factor):
        """Extend or shrink the edges along the line from start of the first edge to the 
        end of the last edge in sequence
        """
        # TODOLOW Version With preservation of total length?
        # TODOLOW Base extention factor on change in total length of edges rather
        # than on the shortcut length

        # FIXME extending by negative factor should be predictable (e.g. opposite direction of extention)

        # Need to take the target line from the chained order
        if not self.isChained():  
            chained_edges = self.chained_order()
            chained_edges.isChained()
            if chained_edges.isLoop():
                print(f'{self.__class__.__name__}::Warning::Extending looped edge sequences is not available')
                return self
        else: 
            chained_edges = self
        
        target_line = np.array(chained_edges[-1].end) - np.array(chained_edges[0].start)
        target_line = target_line / norm(target_line)

        # gather vertices
        verts_coords = self.verts()
        nverts_coords = np.array(verts_coords)
        
        # adjust their position based on projection to the target line
        verts_projection = np.empty(nverts_coords.shape)
        fixed = nverts_coords[0]
        for i in range(nverts_coords.shape[0]):
            verts_projection[i] = (nverts_coords[i] - fixed).dot(target_line) * target_line

        new_verts = verts_coords - (1 - factor) * verts_projection

        # Update vertex objects
        for i in range(len(verts_coords)):
            verts_coords[i][:] = new_verts[i]

        return self

    def reflect(self, v0, v1):
        """Reflect 2D points w.r.t. 1D line defined by two points"""
        v0, v1 = np.asarray(v0), np.asarray(v1)
        vec = np.asarray(v1) - np.asarray(v0)
        vec = vec / norm(vec)  # normalize

        # https://demonstrations.wolfram.com/ReflectionMatrixIn2D/#more
        Ref = np.array([
            [ 1 - 2 * vec[1]**2,  2*vec[0]*vec[1]],
            [ 2*vec[0]*vec[1],    - 1 + 2 * vec[1]**2 ]
            ])
        
        # translate -> reflect -> translate back
        for v in self.verts():
            v[:] = np.matmul(Ref, np.asarray(v) - v0) + v0

        # Reflect edge features (curvatures, etc.)
        for e in self.edges:
            e.reflect_features()

        return self

    # ANCHOR New sequences & versions
    def copy(self):
        """Create a copy of a current edge sequence preserving the chaining property of edge sequences"""
        new_seq = deepcopy(self)

        # deepcopy recreates the vertex objects on both sides of the edges
        # in chaned edges those vertex objects are supposed to be shared
        # by neighbor edges

        for i in range(1, len(new_seq)):
            if self[i].start is self[i-1].end:
                new_seq[i].start = new_seq[i-1].end
            
        if self.isLoop():
            new_seq[-1].end = new_seq[0].start

        return new_seq

    def chained_order(self):
        """ Attempt to restore a chain in the EdgeSequence
            The chained edge sequence may loose it's property if the edges were reveresed externally. 
            This routine created a copy of the currect sequence with aligned the order of edges,

            It might be useful for various calculations
        
        """
        chained = self.copy()
        
        for i in range(len(chained)):
            # Assuming the previous one is already sorted
            if i > 0 and chained[i].end is chained[i-1].end:
                chained[i].reverse()
            # Not connected to the previous one
            elif (i + 1 < len(chained)
                    and (chained[i].start is chained[i+1].start or chained[i].start is chained[i+1].end)):
                chained[i].reverse()
            # not connected to anything or connected properly -- leave as is
        
        return chained