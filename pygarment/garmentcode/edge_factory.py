import numpy as np
from numpy.linalg import norm
import svgpathtools as svgpath
from scipy.optimize import minimize

from pygarment.garmentcode.edge import EdgeSequence, Edge, CurveEdge
from pygarment.garmentcode.edge import CircleEdge
from pygarment.garmentcode.utils import vector_angle
from pygarment.garmentcode.utils import bbox_paths
from pygarment.garmentcode.utils import close_enough
from pygarment.garmentcode.utils import c_to_list
from pygarment.garmentcode.utils import list_to_c
from pygarment.pattern.utils import rel_to_abs_2d, abs_to_rel_2d


class EdgeFactory:
    @staticmethod
    def from_svg_curve(seg):
        """Create Edge/CurveEdge/CircleEdge object from svgpath object
            Type is determined by svgpath type
        """

        start, end = c_to_list(seg.start), c_to_list(seg.end)
        if isinstance(seg, svgpath.Line):
            return Edge(start, end)
        if isinstance(seg, svgpath.Arc):
            # NOTE: assuming circular arc (same radius in both directoins)
            radius = seg.radius.real
            return CircleEdgeFactory.from_points_radius(
                start, end, radius, seg.large_arc, seg.sweep
            )

        # Only Bezier left
        if isinstance(seg, svgpath.QuadraticBezier):
            cp = [c_to_list(seg.control)]
        elif isinstance(seg, svgpath.CubicBezier):
            cp = [c_to_list(seg.control1), c_to_list(seg.control2)]
        else:
            raise NotImplementedError(f'CurveEdge::ERROR::Incorrect curve type supplied {seg.type}')
        
        return CurveEdge(start, end, cp, relative=False)

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
        if close_enough(radius ** 2, str_dist ** 2 / 4, 1e-3):
            center_r = 0.
        else:
            center_r = np.sqrt(radius ** 2 - str_dist ** 2 / 4)

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
                f'CircleEdge::ERROR::Incorrect length for specified radius')

        large_arc = length > max_len / 2
        if large_arc:
            length = max_len - length

        w_half = rad * np.sin(length / rad / 2)

        edge = CircleEdgeFactory.from_points_radius(
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
    def from_three_points(start, end, point_on_arc, relative=False):
        """Create a circle arc from 3 points (start, end and any point on an arc)

            NOTE: Control point specified in the same coord system as start and end
            NOTE: points should not be on the same line
        """
        if relative:
            point_on_arc = rel_to_abs_2d(start, end, point_on_arc)

        nstart, nend, npoint_on_arc = np.asarray(start), np.asarray(
            end), np.asarray(point_on_arc)

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
            start, end, radius=rad,
            large_arc=mid_dist > rad, right=angle > 0)

class CurveEdgeFactory:
    @staticmethod
    def curve_3_points(start, end, target, verbose=False):
        """Create (Quadratic) curve edge between start and end that
            passes through the target point 
        """
        rel_target = abs_to_rel_2d(start, end, target)

        if rel_target[0] > 1 or rel_target[0] < 0:
            raise NotImplementedError(
                "CurveEdgeFactory::Curve_by_3_points::ERROR::requested target point's projection "
                "is outside of the base edge, which is not yet supported"
            )

        # Initialization with a target point as control point
        # Ensures very smooth, minimal solution
        out = minimize(
            _fit_pass_point, 
            rel_target,    
            args=(rel_target)
        )

        if not out.success:
            if verbose:
                print('Curve From Extreme::WARNING::Optimization not successful')
                print(out)

        cp = out.x.tolist()

        return CurveEdge(start, end, control_points=[cp], relative=True)

    @staticmethod
    def curve_from_tangents(start, end, target_tan0=None, target_tan1=None,
                            initial_guess=None, verbose=False):
        """Create Quadratic Bezier curve connecting given points with the target tangents
            (both or any of the two can be specified)
        
            NOTE: Target tangent vectors are automatically normalized
        """

        if target_tan0 is not None:
            target_tan0 = abs_to_rel_2d(start, end, target_tan0, as_vector=True)
            target_tan0 /= norm(target_tan0)
        
        if target_tan1 is not None:
            target_tan1 = abs_to_rel_2d(start, end, target_tan1, as_vector=True)
            target_tan1 /= norm(target_tan1)
        
        # Initialization with a target point as control point
        # Ensures very smooth, minimal solution
        out = minimize(
            _fit_tangents, 
            [0.5, 0] if initial_guess is None else initial_guess,
            args=(target_tan0, target_tan1)
        )

        if not out.success:
            print('CurveEdgeFactory::Curve From Tangents::WARNING::Optimization not successful')
            if verbose:
                print(out)

        cp = out.x.tolist()

        return CurveEdge(start, end, control_points=[cp], relative=True)

class EdgeSeqFactory:
    """Create EdgeSequence objects for some common edge sequence patterns
    """
    @staticmethod
    def from_svg_path(path: svgpath.Path, dist_tol=0.05, verbose=False):
        """Convert SVG path given as svgpathtool Path object to an EdgeSequence

        * dist_tol: tolerance for vertex closeness to be considered the same
            vertex
            NOTE: Assumes that the path can be chained
        """
        # Convert as is
        edges = []
        for seg in path._segments:
            # skip segments of length zero
            if close_enough(seg.length(), tol=dist_tol):
                if verbose:
                    print('Skipped: ', seg)
                continue
            edges.append(EdgeFactory.from_svg_curve(seg))

        # Chain the edges
        if len(edges) > 1:
            for i in range(1, len(edges)):

                if not all(close_enough(s, e, tol=dist_tol)
                           for s, e in zip(edges[i].start, edges[i - 1].end)):
                    raise ValueError(
                        'EdgeSequence::from_svg_path::input path is not chained')

                edges[i].start = edges[i - 1].end
        return EdgeSequence(*edges, verbose=verbose)

    @staticmethod
    def from_verts(*verts, loop=False):
        """Generate sequence of straight edges from given vertices. If loop==True,
         the method also closes the edge sequence as a loop
        """
        seq = EdgeSequence(Edge(verts[0], verts[1]))
        for i in range(2, len(verts)):
            seq.append(Edge(seq[-1].end, verts[i]))

        if loop:
            seq.append(Edge(seq[-1].end, seq[0].start))
        
        seq.isChained()  # print warning if smth is wrong
        return seq

    @staticmethod
    def from_fractions(start, end, frac=None):
        """A sequence of edges between start and end wich lengths are distributed
            as specified in frac list 
        Parameters:
            * frac -- list of legth fractions. Every entry is in (0, 1], 
                all entries sums up to 1
        """
        frac = [abs(f) for f in frac]
        if not close_enough(fsum := sum(frac), 1, 1e-4):
            raise RuntimeError(f'EdgeSequence::ERROR::fraction is incorrect. The sum {fsum} is not 1')

        vec = np.asarray(end) - np.asarray(start)
        verts = [start]
        for i in range(len(frac) - 1):
            verts.append(
                [verts[-1][0] + frac[i]*vec[0],
                verts[-1][1] + frac[i]*vec[1]]
            )
        verts.append(end)
        
        return EdgeSeqFactory.from_verts(*verts)

    @staticmethod
    def side_with_cut(start=(0, 0), end=(1, 0), start_cut=0, end_cut=0):
        """ Edge with internal vertices that allows to stitch only part of the border represented
            by the long side edge

            start_cut and end_cut specify the fraction of the edge to to add extra vertices at
        """
        nstart, nend = np.array(start), np.array(end)
        verts = [start]

        if start_cut > 0:
            verts.append((start + start_cut * (nend-nstart)).tolist())
        if end_cut > 0:
            verts.append((end - end_cut * (nend-nstart)).tolist())
        verts.append(end)

        edges = EdgeSeqFactory.from_verts(*verts)

        return edges

    # ------ Darts ------
    @staticmethod
    def dart_shape(width, side_len=None, depth=None):
        """Shape of simple triangular dart: 
            specified by desired width and either the dart side length or depth
        """

        if side_len is None and depth is None:
            raise ValueError(
                'EdgeFactory::ERROR::dart shape is not fully specified.'
                ' Add dart side length or dart perpendicular'
            )

        if depth is None:
            if width / 2 > side_len: 
                raise ValueError(
                    f'EdgeFactory::ERROR::Requested dart shape (w={width}, side={side_len}) '
                    'does not form a valid triangle')
            depth = np.sqrt((side_len**2 - (width / 2)**2))

        return EdgeSeqFactory.from_verts([0, 0], [width / 2, -depth], [width, 0])

    # --- SVG ----
    @staticmethod
    def halfs_from_svg(svg_filepath, target_height=None):
        """Load a shape from an SVG and split it in half (vertically)

        * target_height -- scales the shape s.t. it's height matches the given
            number
        
        Shapes restrictions: 
            1) every path in the provided SVG is assumed to form a closed loop
                that has exactly 2 intersection points with a vertical line
                passing though the middle of the shape
            2) The paths should not be nested (inside each other) or intersect
                as to not create disconnected pieces of the edge when used in
                shape projection
        """
        paths, _ = svgpath.svg2paths(svg_filepath)

        # Scaling
        if target_height is not None:
            bbox = bbox_paths(paths)
            scale = target_height / (bbox[-1] - bbox[-2])
            paths = [p.scaled(scale) for p in paths]

        # Get the half-shapes
        left, right = split_half_svg_paths(paths)

        # Turn into Edge Sequences
        left_seqs = [EdgeSeqFactory.from_svg_path(p) for p in left]
        right_seqs = [EdgeSeqFactory.from_svg_path(p) for p in right]

        # In SVG OY is looking downward, we are using OY looking upward
        # Flip the shape to align
        bbox = bbox_paths(paths)
        center_y = (bbox[2] + bbox[3]) / 2
        left_seqs = [p.reflect([bbox[0], center_y],
                               [bbox[1], center_y]) for p in left_seqs]
        right_seqs = [p.reflect([bbox[0], center_y],
                                [bbox[1], center_y]) for p in right_seqs]

        # Edge orientation s.t. the shortcut directions align with OY
        # It preserves the correct relative placement of the shapes later
        for p in left_seqs:
            if (p.shortcut()[1][1] - p.shortcut()[0][1]) < 0:
                p.reverse()
        for p in right_seqs:
            if (p.shortcut()[1][1] - p.shortcut()[0][1]) < 0:
                p.reverse()

        return left_seqs, right_seqs

# --- For Curves ---
def _fit_pass_point(cp, target_location):
    """ Fit the control point of basic [[0, 0] -> [1, 0]] Quadratic Bezier s.t. 
        it passes through the target location.

        * cp - initial guess for Quadratic Bezier control point coordinates
            (relative to the edge)
        * target_location -- target to fit extremum to --
            expressed in RELATIVE coordinates to your desired edge
    """
    control_bezier = np.array([
        [0, 0],
        cp,
        [1, 0]
    ])
    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    inter_segment = svgpath.Line(
            target_location[0] + 1j * target_location[1] * 2,
            target_location[0] + 1j * (- target_location[1] * 2)
        )

    intersect_t = curve.intersect(inter_segment)
    point = curve.point(intersect_t[0][0])

    diff = abs(point - list_to_c(target_location))

    return diff**2


def _fit_tangents(cp, target_tangent_start, target_tangent_end, reg_strength=0.01):
    """ Fit the control point of basic [[0, 0] -> [1, 0]] Quadratic Bezier s.t. 
        it's expremum is close to target location.

        * cp - initial guess for Quadratic Bezier control point coordinates
            (relative to the edge)
        * target_location -- target to fit extremum to -- 
            expressed in RELATIVE coordinates to your desired edge
    """
    control_bezier = np.array([
        [0, 0], 
        cp, 
        [1, 0]
    ])
    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    fin = 0
    if target_tangent_start is not None: 
        # NOTE: tangents seems to use opposite left/right convention
        target0 = target_tangent_start[0] + 1j*target_tangent_start[1]
        fin += (abs(curve.unit_tangent(0) - target0))**2
    
    if target_tangent_end is not None: 
        target1 = target_tangent_end[0] + 1j*target_tangent_end[1]
        fin += (abs(curve.unit_tangent(1) - target1))**2

    # NOTE: Tried _max_curvature() and Y value regularizaton, 
    # but it seems like they are not needed
    return fin


# ---- For SVG Loading ----

def split_half_svg_paths(paths):
    """Sepate SVG paths in half over the vertical line -- for insertion into an
        edge side

        Paths shapes restrictions:
        1) every path in the provided list is assumed to form a closed loop
            that has
        exactly 2 intersection points with a vetrical line passing though the
            middle of the shape
        2) The paths geometry should not be nested
            as to not create disconnected pieces of the edge when used in
                shape projection

    """
    # Shape Bbox
    bbox = bbox_paths(paths)
    center_x = (bbox[0] + bbox[1]) / 2

    # Mid-Intersection
    inter_segment = svgpath.Line(
            center_x + 1j * bbox[2],
            center_x + 1j * bbox[3]
        )

    right, left = [], []
    for p in paths:
        # Intersect points
        intersect_t = p.intersect(inter_segment)

        if len(intersect_t) != 2:
            raise ValueError(f'SplitSVGHole::ERROR::Each Provided Svg path should cross vertical like exactly 2 times')

        # Split
        from_T, to_T = intersect_t[0][0][0], intersect_t[1][0][0]
        if to_T < from_T:
            from_T, to_T = to_T, from_T

        side_1 = p.cropped(from_T, to_T)
        # This order should preserve continuity
        side_2 = svgpath.Path(
            *p.cropped(to_T, 1)._segments,
            *p.cropped(0, from_T)._segments)

        # Collect correctly
        if side_1.bbox()[2] > center_x:
            side_1, side_2 = side_2, side_1

        right.append(side_2)
        left.append(side_1)

    return left, right
