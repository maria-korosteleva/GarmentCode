
import numpy as np
from numpy.linalg import norm
import svgpathtools as svgpath
from scipy.optimize import minimize

# Custom
from .edge import EdgeSequence, Edge, CurveEdge
from .generic_utils import close_enough, c_to_list, list_to_c
from . import flags

class EdgeSeqFactory:
    """Create EdgeSequence objects for some common edge seqeunce patterns
    """

    @staticmethod
    def from_verts(*verts, loop=False):
        """Generate edge sequence from given vertices. If loop==True, the method also closes the edge sequence as a loop
        """

        seq = EdgeSequence(Edge(verts[0], verts[1]))
        for i in range(2, len(verts)):
            seq.append(Edge(seq[-1].end, verts[i]))

        if loop:
            seq.append(Edge(seq[-1].end, seq[0].start))
        
        seq.isChained()
        return seq

    @staticmethod
    def from_fractions(start, end, frac=[1]):
        """A sequence of edges between start and end wich lengths are distributed
            as specified in frac list 
        Parameters:
            * frac -- list of legth fractions. Every entry is in (0, 1], 
                all entries sums up to 1
        """
        frac = [abs(f) for f in frac]
        if not close_enough(fsum:=sum(frac), 1, 1e-4):
            raise RuntimeError(f'EdgeSequence::Error::fraction is incorrect. The sum {fsum} is not 1')

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
    def side_with_cut(start=(0,0), end=(1,0), start_cut=0, end_cut=0):
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

    @staticmethod
    def dart_shape(width, side_len=None, depth=None):
        """Shape of simple triangular dart: 
            specified by desired width and either the dart side length or depth
        """

        if side_len is None and depth is None:
            raise ValueError(
                'EdgeFactory::Error::dart shape is not fully specified.'
                ' Add dart side length or dart perpendicular'
            )

        if depth is None:
            if width / 2 > side_len: 
                raise ValueError(
                    f'EdgeFactory::Error::Requested dart shape (w={width}, side={side_len}) '
                    'does not form a valid triangle')
            depth = np.sqrt((side_len**2 - (width / 2)**2))

        return EdgeSeqFactory.from_verts([0, 0], [width / 2, -depth], [width, 0])

    @staticmethod
    def curve_from_extreme(start, end, target):
        """Create (Quadratic) curve edge that 
            has an extreme point as close as possible to target_extreme
            with extreme point aligned with it
        """
        rel_target = _abs_to_rel_2d(start, end, target)

        out = minimize(
            _fit_y_extremum, 
            rel_target[1],    
            args=(rel_target)
        )

        if not out.success:
            print('Curve From Extreme::WARNING::Optimization not successful')
            if flags.VERBOSE:
                print(out)

        cp = [rel_target[0], out.x.item()]

        return CurveEdge(start, end, control_points=[cp], relative=True)
    
    @staticmethod
    def curve_3_points(start, end, target):
        """Create (Quadratic) curve edge between start and end that
            passes through the target point 
        """
        rel_target = _abs_to_rel_2d(start, end, target)

        if rel_target[0] > 1 or rel_target[0] < 0:
            raise NotImplementedError(
                f"EdgeFactory::Curve_by_3_points::ERROR::requested target point's projection "
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
            print('Curve From Extreme::WARNING::Optimization not successful')
            if flags.VERBOSE:
                print(out)

        cp = out.x.tolist()

        return CurveEdge(start, end, control_points=[cp], relative=True)

    @staticmethod
    def curve_from_len_tangents(start, end, cp, target_len, target_tan0, target_tan1):
        """Find a curve with given relative curvature parameters"""

# Utils
def _abs_to_rel_2d(start, end, point):
    """Convert control points coordinates from absolute to relative"""
    start, end = np.asarray(start), np.asarray(end)
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

def _extreme_points(curve, on_x=False, on_y=True):
    """Return extreme points of the input curve
        NOTE: this does NOT include the border vertices of an edge
    """
    # Variation of https://github.com/mathandy/svgpathtools/blob/5c73056420386753890712170da602493aad1860/svgpathtools/bezier.py#L197
    poly = svgpath.bezier2polynomial(curve, return_poly1d=True)
    
    x_extremizers, y_extremizers = [], []
    if on_y:
        y = svgpath.imag(poly)
        dy = y.deriv()
        
        y_extremizers = svgpath.polyroots(dy, realroots=True,
                                            condition=lambda r: 0 < r < 1)
    if on_x:
        x = svgpath.real(poly)
        dx = x.deriv()
        x_extremizers = svgpath.polyroots(dx, realroots=True,
                                    condition=lambda r: 0 < r < 1)
    all_extremizers = x_extremizers + y_extremizers

    extreme_points = np.array([c_to_list(curve.point(t)) for t in all_extremizers])

    return extreme_points

def _fit_y_extremum(cp_y, target_location):
    """ Fit the control point of basic [[0, 0] -> [1, 0]] Quadratic Bezier s.t. 
        it's expremum is close to target location.

        * cp_y - initial guess for Quadratic Bezier control point y coordinate
            (relative to the edge)
        * target_location -- target to fit extremum to -- 
            expressed in RELATIVE coordinates to your desired edge
    """

    control_bezier = np.array([
        [0, 0], 
        [target_location[0], cp_y[0]], 
        [1, 0]
    ])
    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    extremum = _extreme_points(curve)

    if not len(extremum):
        raise RuntimeError('No extreme points!!')

    diff = np.linalg.norm(extremum - target_location)

    return diff**2 

def _fit_pass_point(cp, target_location):
    """ Fit the control point of basic [[0, 0] -> [1, 0]] Quadratic Bezier s.t. 
        it's expremum is close to target location.

        * cp_y - initial guess for Quadratic Bezier control point y coordinate
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
