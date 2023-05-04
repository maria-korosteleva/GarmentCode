import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
import svgpathtools as svgpath
from copy import copy, deepcopy

# Custom
import pypattern as pyp
from . import bands

# ------  Armhole shapes ------
def ArmholeSquare(incl, width, angle, **kwargs):
    """Simple square armhole cut-out
        Not recommended to use for sleeves, stitching in 3D might be hard

        if angle is provided, it also calculated the shape of the sleeve interface to attach

        returns edge sequence and part to be preserved  inverted 
    """

    edges = pyp.esf.from_verts([0, 0], [incl, 0],  [incl, width])

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyp.esf.from_verts(
        [incl + l*sina, - l*cosa], 
        [incl, 0],  [incl, width])
    
    # TODO Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle) 

    return edges, sleeve_edges


def ArmholeSmooth(incl, width, angle, incl_coeff=0.2, w_coeff=0.2):
    """Piece-wise smooth armhole shape"""
    diff_incl = incl * (1 - incl_coeff)
    edges = pyp.esf.from_verts([0, 0], [diff_incl, w_coeff * width],  [incl, width])

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyp.esf.from_verts(
        [diff_incl + l*sina, w_coeff * width - l*cosa], 
        [diff_incl, w_coeff * width],  [incl, width])
    # TODO Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle) 

    return edges, sleeve_edges


def _avg_curvature(curve, points_estimates=100):
    """Average curvature in a curve"""
    t_space = np.linspace(0, 1, points_estimates)
    return sum([curve.curvature(t) for t in t_space]) / points_estimates


def _bend_extend_2_tangent(shift, cp, target_len, direction, target_tangent_start, target_tangent_end):

    control = np.array([
        cp[0], 
        [cp[1][0] + shift[0], cp[1][0] + shift[1]], 
        [cp[2][0] + shift[2], cp[2][0] + shift[3]],
        cp[-1] + direction * shift[4]
    ])

    params = control[:, 0] + 1j*control[:, 1]
    curve_inverse = svgpath.CubicBezier(*params)

    length_diff = (curve_inverse.length() - target_len)**2  # preservation

    tan_0_diff = (abs(curve_inverse.unit_tangent(0) - target_tangent_start))**2
    tan_1_diff = (abs(curve_inverse.unit_tangent(1) - target_tangent_end))**2

    curvature_reg = _avg_curvature(curve_inverse)**2
    end_expantion_reg = 0.001*shift[-1]**2 

    return length_diff + tan_0_diff + tan_1_diff + curvature_reg + end_expantion_reg
      


def ArmholeCurve(incl, width, angle, **kwargs):
    """ Classic sleeve opening on Cubic Bezier curves
    """

    # Curvature as parameters?
    cps = [[0.5, 0.2], [0.8, 0.35]]
    edge = pyp.CurveEdge([incl, width], [0, 0], cps)

    # Inverse
    curve = edge.as_curve()
    tangent = np.array([0, -1])  # Full opening is vertically aligned
    inv_end = np.array([incl, width]) + tangent * edge._straight_len()

    inv_cps = deepcopy(cps)
    inv_cps[-1][1] *= -1  # Invert the last 

    inv_edge = pyp.CurveEdge(
        [incl, width], 
        inv_end.tolist(), 
        inv_cps
        )
    
    # Rotate by desired angle
    inv_edge.rotate(angle=-angle)

    # Optimize the shape to be nice
    curve_inv = inv_edge.as_curve()
    shortcut = inv_edge.shortcut()
    direction = shortcut[-1] - shortcut[0]
    direction /= np.linalg.norm(direction)
    curve_cps = pyp.utils.c_to_np(curve_inv.bpoints())

    # match tangent with the sleeve opening while preserving length
    out = minimize(
        _bend_extend_2_tangent, # with tangent matching
        [0, 0, 0, 0, 0], 
        args=(
            curve_cps, 
            curve.length(),
            direction,
            pyp.utils.list_to_c(tangent),  
            pyp.utils.list_to_c(direction), 
        )
    )
    if not out.success:
        print(f'ArmholeCurve::Error::Inverse optimization not successfull')
        if pyp.flags.VERBOSE:
            print(out)

    shift = out.x

    # Final inverse edge
    fin_inv_edge = pyp.CurveEdge(
        start=curve_cps[0].tolist(), 
        end=(curve_cps[-1] + direction*shift[-1]).tolist(), 
        control_points=[
            [curve_cps[1][0] + shift[0], curve_cps[1][0] + shift[1]], 
            [curve_cps[2][0] + shift[2], curve_cps[2][0] + shift[3]],
        ],
        relative=False
    )

    return pyp.EdgeSequence(edge.reverse()), pyp.EdgeSequence(fin_inv_edge.reverse())


# TODO Move
def ArmholeOpeningEvening(front_opening, back_opening):
    """
        Rearrange sleeve openings for front and back s.t. we can costruct 
        two symmetric sleebe panels from them

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
        pyp.list_to_c(slope_midpoint - 20 * slope_perp), 
        pyp.list_to_c(slope_midpoint + 20 * slope_perp)
    )
    target_segment = cfront[-1].as_curve()

    intersect_t = target_segment.intersect(inter_segment)
    if len(intersect_t) > 1:
        raise RuntimeError(
            f'Sleeve Opening Inversion::Error::{len(intersect_t)} intersection points instead of one'
        )
    intersect_t = intersect_t[0][0]

    if not pyp.utils.close_enough(intersect_t, 0, tol=0.01):
        # The current separation is not satisfactory
        # Update the opening shapes
        subdiv = front_opening.edges[-1].subdivide_param([intersect_t, 1 - intersect_t])
        front_opening.substitute(-1, subdiv[0])  

        # Move this part to the back opening
        subdiv[1].start, subdiv[1].end = copy(subdiv[1].start), copy(subdiv[1].end)  # Disconnect vertices in subdivided version
        subdiv.pop(0)   # TODO No reflect in the edge class??
        subdiv.reflect([0, 0], [1, 0]).reverse().snap_to(back_opening[-1].end)
        subdiv[0].start = back_opening[-1].end
        
        back_opening.append(subdiv[0])

    # Align the slope with OY direction
    # for correct size of sleeve panels
    slope_angle = np.arctan(-slope_vec[0] / slope_vec[1])	
    front_opening.rotate(-slope_angle)
    back_opening.rotate(slope_angle)

    return front_opening, back_opening


# -------- New sleeve definitions -------

class ExperimentalSleevePanel(pyp.Panel):
    """Trying proper sleeve panel"""

    def __init__(self, name, body, design, open_shape):
        super().__init__(name)

        # TODO end_width to be not less then the width of the arm??

        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        rest_angle = np.deg2rad(design['sleeve_angle']['v'])
        standing = design['standing_shoulder']['v']

        length = design['length']['v']

        # Sleeve width with accounting for ruffles
        end_width = design['end_width']['v'] / 2 * design['end_ruffle']['v']
        if not pyp.utils.close_enough(design['connect_ruffle']['v'], 1):
            open_shape.extend(design['connect_ruffle']['v'])

        # Correct sleeve width -- after aligning rotation
        arm_width = abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # Main body of a sleeve 
        self.edges = pyp.esf.from_verts(
            [0, 0], [0, -end_width], [length, -arm_width]
        )

        # Align the opening
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)
        # Fin
        self.edges.close_loop()

        if standing and rest_angle > shoulder_angle:  # Add a "shelve" to create square shoulder appearance
            top_edge = self.edges[-1]
            start = top_edge.start
            len = design['standing_shoulder_len']['v']

            x_shift = len * np.cos(rest_angle - shoulder_angle)
            y_shift = len * np.sin(rest_angle - shoulder_angle)

            standing_edge = pyp.Edge(
                start=start,
                end=[start[0] - x_shift, start[1] + y_shift]
            )
            top_edge.start = standing_edge.end

            self.edges.substitute(top_edge, [standing_edge, top_edge])


        # Interfaces
        self.interfaces = {
            # NOTE: interface needs reversing because the open_shape was reversed for construction
            'in': pyp.Interface(self, open_shape, ruffle=design['connect_ruffle']['v']),
            'out': pyp.Interface(self, self.edges[0], ruffle=design['end_ruffle']['v']),
            'top': pyp.Interface(self, self.edges[-2:] if standing else self.edges[-1]),  
            'bottom': pyp.Interface(self, self.edges[1])
        }

        # Default placement
        self.set_pivot(self.edges[1].end)
        self.translate_to(
            [- body['sholder_w'] / 2,
            body['height'] - body['head_l'] - body['armscye_depth'],
            0]) 
        self.rotate_to(R.from_euler(
            'XYZ', [0, 0, body['arm_pose_angle']], degrees=True))


class ExperimentalSleeve(pyp.Component):
    """Trying to do a proper sleeve"""


    def __init__(self, tag, body, design, depth_diff=3) -> None: 
        super().__init__(f'{self.__class__.__name__}_{tag}')

        design = design['sleeve']
        inclanation = design['inclanation']['v']

        # TODO Min with shoulder angle? 
        rest_angle = np.deg2rad(design['sleeve_angle']['v'])

        connecting_width = design['connecting_width']['v']
        smoothing_coeff = design['smoothing_coeff']['v']

        # Define sleeve opening shapes
        armhole = globals()[design['armhole_shape']['v']]
        front_project, front_opening = armhole(
            inclanation + depth_diff, connecting_width, 
            angle=rest_angle, incl_coeff=smoothing_coeff, w_coeff=smoothing_coeff)
        
        back_project, back_opening = armhole(
            inclanation, connecting_width, 
            angle=rest_angle, incl_coeff=smoothing_coeff, w_coeff=smoothing_coeff)

        if depth_diff != 0: 
            front_opening, back_opening = ArmholeOpeningEvening(
                front_opening, back_opening
            )

        # Get sleeve panels
        self.f_sleeve = ExperimentalSleevePanel(
            f'{tag}_sleeve_f', body, design, front_opening).translate_by(
                [-inclanation - depth_diff, 0, 25])
        self.b_sleeve = ExperimentalSleevePanel(
            f'{tag}_sleeve_b', body, design, back_opening).translate_by(
                [-inclanation, 0, -20])

        # Connect panels
        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces['top'], self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'], self.b_sleeve.interfaces['bottom']),
        )

        # Interfaces
        self.interfaces = {
            'in_front_shape': pyp.Interface(self.f_sleeve, front_project),
            'in_back_shape': pyp.Interface(self.f_sleeve, back_project), 
            'in': pyp.Interface.from_multiple(
                self.f_sleeve.interfaces['in'].reverse(),
                self.b_sleeve.interfaces['in'].reverse()
            ),
            'out': pyp.Interface.from_multiple(
                    self.f_sleeve.interfaces['out'], 
                    self.b_sleeve.interfaces['out']
                ),
        }

        # Cuff
        if design['cuff']['type']['v']:
            # Class
            design['cuff']['b_width'] = design['end_width']
            cuff_class = getattr(bands, design['cuff']['type']['v'])
            self.cuff = cuff_class(f'sl_{tag}', design)

            # Position
            self.cuff.rotate_by(
                R.from_euler(
                    'XYZ', 
                    [0, 0, -90 + body['arm_pose_angle']],   # from -Ox direction
                    degrees=True
                )
            )
            self.cuff.place_by_interface(
                self.cuff.interfaces['top'],
                self.interfaces['out'],
                gap=5
            )

            self.stitching_rules.append(
                (
                    self.cuff.interfaces['top'], 
                    self.interfaces['out']
                )
            )
            
            # UPD out interface!
            self.interfaces['out'] = self.cuff.interfaces['bottom']
