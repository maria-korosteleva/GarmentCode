from numpy.linalg import norm
import numpy as np
import matplotlib.pyplot as plt
from svgpathtools import QuadraticBezier, CubicBezier
import svgpathtools as svgpath
from scipy.optimize import minimize
from copy import copy
import sys

sys.path.insert(0, './external/')
sys.path.insert(1, './')

from pypattern.generic_utils import c_to_list, list_to_c, c_to_np


def _abs_to_rel_2d(in_edge, point):
    """Convert control points coordinates from absolute to relative"""
    start, end = np.array(in_edge[0]), np.array(in_edge[1])
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

def _rel_to_abs_2d(in_edge, point):
    """Convert coordinates expressed relative to an edge into absolute """
    start, end = np.array(in_edge[0]), np.array(in_edge[1])
    edge = end - start
    edge_perp = np.array([-edge[1], edge[0]])

    conv_start = start + point[0] * edge
    conv_point = conv_start + point[1] * edge_perp
    
    return conv_point


# Creating a quadratic / cubic curve by endpoints and desired extrema location

def plot_bezier_curve(
        curve=None, 
        control_points=None, bounding_points=None, extreme_points=None, tag='Bezier'):
    
    if control_points is not None:
        control_points = np.asarray(control_points)
    if extreme_points is not None:
        extreme_points = np.asarray(extreme_points)
    if not curve:
        params = list_to_c(control_points)
        curve = QuadraticBezier(*params) if len(control_points) == 3 else CubicBezier(*params)

    t_values = np.linspace(0, 1, num=1000)
    curve_points = np.array([c_to_list(curve.point(t)) for t in t_values])

    plt.plot(curve_points[:, 0], curve_points[:, 1], label=tag + " Curve")
    # plt.scatter([p.real for p in extreme_points], [p.imag for p in extreme_points], color='red', label="Extreme Points")
    
    if control_points is not None:
        plt.scatter(control_points[:, 0], control_points[:, 1], label=tag + " Control Points")

    if extreme_points is not None:
        plt.scatter(extreme_points[:, 0], extreme_points[:, 1], color='red', label=tag + " Extreme Points")
    
    if bounding_points is not None:
        plt.scatter(bounding_points[:, 0], bounding_points[:, 1], color='yellow', label=tag + " Control Points")

def _extreme_points(curve, on_x=False, on_y=True):
    """Return extreme points of the current edge
        NOTE: this does NOT include the border vertices of an edge
    """

    # TODO alight the curve opening with Oy and Ox and then evaluate the extremizers
    # Otherwise it doesn't reflect local shape
    # OR do it in local coordinates

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

    # # DEBUG
    # print('Extremes calculation')
    # print(poly)
    # print(x, dx)
    # print(x_extremizers)
    # print(y, dy)
    # print(y_extremizers)

    extreme_points = np.array([c_to_list(curve.point(t)) for t in all_extremizers])

    return extreme_points

def _fit_quadratic_y_extrema(cp, ends, target_location):

    control_bezier = np.array([
        ends[0], 
        [target_location[0], cp[1]],   # cp,  # DRAFT 
        ends[-1]
    ])

    dir0 = target_location - ends[0]
    dir0 = dir0 / norm(dir0)

    dir1 = - (target_location - ends[1])
    dir1 = dir1 / norm(dir1)

    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    extreme = _extreme_points(curve)

    if not len(extreme):
        raise RuntimeError('No extreme points!!')

    diff = np.linalg.norm(extreme - target_location)

    tan0_diff = norm(curve.unit_tangent(0) - dir0)
    tan1_diff = norm(curve.unit_tangent(1) - dir1)

    #DEBUG 
    print('Inter: ', diff, extreme)

    return diff**2 + 0.01 * (tan0_diff**2 + tan1_diff**2)


def _fit_extrema_quadratic(cp, ends, target_location):

    control_bezier = np.array([
        ends[0], 
        cp,  # DRAFT [target_location[0], cp[1]], 
        ends[-1]
    ])

    dir0 = target_location - ends[0]
    dir0 = dir0 / norm(dir0)

    dir1 = - (target_location - ends[1])
    dir1 = dir1 / norm(dir1)

    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    extreme = _extreme_points(curve)

    if not len(extreme):
        raise RuntimeError('No extreme points!!')

    diff = np.linalg.norm(extreme - target_location)

    tan0_diff = norm(curve.unit_tangent(0) - dir0)
    tan1_diff = norm(curve.unit_tangent(1) - dir1)

    #DEBUG 
    print('Inter: ', diff, extreme)

    return diff**2   #  + 0.01 * (tan0_diff**2 + tan1_diff**2)

def _fit_quadratic_y_pass(cp, ends, target_location):

    # NOTE: Only relarive expectation!
    control_bezier = np.array([
        ends[0], 
        [target_location[0], cp[1]], 
        ends[-1]
    ])

    # TODO the point directly below the control point is at the target location

    inter_segment = svgpath.Line(
            target_location[0] + 1j * cp[1],
            target_location[0] + 1j * 0
        )

    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    intersect_t = curve.intersect(inter_segment)
    point = curve.point(intersect_t[0][0])

    diff = abs(point - list_to_c(target_location))
    

    #DEBUG 
    print('Inter: ', diff, intersect_t, point, list_to_c(target_location))

    return diff**2


def _fit_quadratic_pass(cp, ends, target_location):

    # NOTE: Only relarive expectation!
    control_bezier = np.array([
        ends[0], 
        cp, 
        ends[-1]
    ])

    # TODO the point directly below the control point is at the target location

    inter_segment = svgpath.Line(
            target_location[0] + 1j * target_location[1] * 2,
            target_location[0] + 1j * (- target_location[1] * 2)
        )

    params = list_to_c(control_bezier)
    curve = svgpath.QuadraticBezier(*params)

    intersect_t = curve.intersect(inter_segment)
    point = curve.point(intersect_t[0][0])

    diff = abs(point - list_to_c(target_location))

    #DEBUG 
    print('Inter: ', diff, intersect_t, point, list_to_c(target_location))
    print('Cp[0]: ', abs(cp[0] - target_location[0]))
    # print('Reg Y ', reg_y)

    return diff**2


# DRAFT bshift, top_shift, length, crotch = 10, 5, 30, 15
# ends = np.array([[bshift, 0], [top_shift, length + crotch]])
# target_extrema_loc = [0, length]

ends = np.array([[0, 0], [1, 0]])
target_extrema_loc = [ 0.70931856, -0.0119797 ]


rel_target = _abs_to_rel_2d(ends, target_extrema_loc)


# Plot initialization
# DEBUG
plot_bezier_curve(
    control_points=[
        [0, 0], rel_target, [1, 0]
    ]
)
plt.gca().set_aspect('equal', adjustable='box')
plt.show()

# DEBUG
control_points=[ends[0], target_extrema_loc, ends[-1]]
curve_init = QuadraticBezier(*list_to_c(control_points))
print(_extreme_points(curve_init))

start = copy(rel_target)
out = minimize(
    _fit_quadratic_pass,  #_fit_extrema_quadratic, #  _fit_quadratic_direct, 
    start,
    args=(
        [[0, 0], [1, 0]],
        rel_target
    )
)

print(out)  # DEBUG

cp = out.x
control_bezier = np.array([
    ends[0],
    _rel_to_abs_2d(ends, cp),
    ends[-1]
])
params = list_to_c(control_bezier)
curve = QuadraticBezier(*params)

plot_bezier_curve(
    curve=curve, 
    control_points=control_bezier, 
    extreme_points=[target_extrema_loc])
plt.title('Curve by Extrema')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.gca().set_aspect('equal', adjustable='box')
plt.show()