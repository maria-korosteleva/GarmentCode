import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
import svgpathtools as svgpath
from copy import copy, deepcopy

import matplotlib.pyplot as plt # DEBUG only

# Custom
import pypattern as pyp
from . import bands

#  ---- Initial sleeve classes ----
class SleevePanel(pyp.Panel):
    def __init__(self, name, body, design, connecting_depth, width_diff=0) -> None:
        super().__init__(name)

        pose_angle = np.deg2rad(body['arm_pose_angle'])
        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        standing = design['standing_shoulder']['v']
        base_angle = pose_angle if standing else shoulder_angle

        length = design['length']['v']
        connecting_width = design['connecting_width']['v']
        smoothing_coeff = design['smoothing_coeff']['v']

        armhole = globals()[design['armhole_shape']['v']]
        proj_shape, open_shape = armhole(
            connecting_depth, connecting_width, 
            angle=base_angle, incl_coeff=smoothing_coeff, w_coeff=smoothing_coeff)

        # Add ruffles
        if not pyp.utils.close_enough(design['connect_ruffle']['v'], 1):
            open_shape.extend(design['connect_ruffle']['v'])

        arm_width = abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # DEBUG
        print('Actual width ', arm_width)
        print('Required width ', design['end_width']['v'])
        print('Estimated width ', design['end_width']['v'] + width_diff)

        # FIXME end_width not used

        # Main body of a sleeve
        self.edges = pyp.esf.from_verts(
            [0, 0], [0, arm_width], [length, arm_width]
        )
        
        # Align the opening
        open_shape.reverse().rotate(-base_angle).snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)

        # align the angle with the pose -- for draping
        self.edges.rotate(pose_angle) 

        if standing:  # Add a "shelve" to create square shoulder appearance
            top_edge = self.edges[1]
            end = top_edge.end
            len = design['standing_shoulder_len']['v']

            standing_edge = pyp.Edge(
                [end[0] - len * np.cos(shoulder_angle), end[1] - len * np.sin(shoulder_angle)], end)
            top_edge.end = standing_edge.start

            self.edges.substitute(top_edge, [top_edge, standing_edge])

        # Fin
        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            # NOTE: interface needs reversing because the open_shape was reversed for construction
            'in': pyp.Interface(self, open_shape, ruffle=design['connect_ruffle']['v']).reverse(),
            'in_shape': pyp.Interface(self, proj_shape),
            'out': pyp.Interface(self, self.edges[0], ruffle=design['end_ruffle']['v']),
            'top': pyp.Interface(self, self.edges[1:3] if standing else self.edges[1]),   
            'bottom': pyp.Interface(self, self.edges[-1])
        }

        # Default placement
        self.set_pivot(self.edges[-1].start)
        self.translate_to(
            [- body['sholder_w'] / 2 - connecting_depth, 
            body['height'] - body['head_l'] - body['armscye_depth'],
            0]) 


class Sleeve(pyp.Component):

    def __init__(self, tag, body, design, depth_diff) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        design = design['sleeve']
        inclanation = design['inclanation']['v']
        
        # sleeves
        self.f_sleeve = SleevePanel(
            f'{tag}_sl_f', body, design, inclanation + depth_diff, depth_diff).translate_by([0, 0, 25])
        self.b_sleeve = SleevePanel(
            f'{tag}_sl_b', body, design, inclanation, -depth_diff).translate_by([0, 0, -20])

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces['top'], self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'], self.b_sleeve.interfaces['bottom']),
        )

        self.interfaces = {
            'in_front': self.f_sleeve.interfaces['in'].reverse(),
            'in_front_shape': self.f_sleeve.interfaces['in_shape'],
            'in_back': self.b_sleeve.interfaces['in'],
            'in_back_shape': self.b_sleeve.interfaces['in_shape'],
        }

        # Cuff
        if design['cuff']['type']['v']:
            bbox = self.bbox3D()

            # Class
            design['cuff']['b_width'] = design['end_width']
            cuff_class = getattr(bands, design['cuff']['type']['v'])
            self.cuff = cuff_class(f'sl_{tag}', design)

            # Position
            pose_angle = np.deg2rad(body['arm_pose_angle'])
            self.cuff.rotate_by(R.from_euler('XYZ', [0, 0, -pose_angle]))

            # Translation
            self.cuff.place_by_interface(
                self.cuff.interfaces['top'],
                pyp.Interface.from_multiple(
                    self.f_sleeve.interfaces['out'], 
                    self.b_sleeve.interfaces['out']
                ),
                gap=5
            )

            # Stitch
            # modify interfaces to control connection
            front_int = self.f_sleeve.interfaces['out'].edges
            frac = design['end_ruffle']['v'] * design['end_width']['v'] / 2 / front_int.length()
            subdiv = pyp.esf.from_fractions(
                front_int[0].start, front_int[0].end, [frac, (1 - frac)])
            self.f_sleeve.edges.substitute(front_int[0], subdiv)

            new_front_int = pyp.Interface(self.f_sleeve, subdiv[0])
            new_back_int = pyp.Interface.from_multiple( 
                pyp.Interface(self.f_sleeve, subdiv[1]),
                self.b_sleeve.interfaces['out'])

            # stitch
            self.stitching_rules.append(  
                (self.cuff.interfaces['top_front'], new_front_int))
            self.stitching_rules.append(
                (self.cuff.interfaces['top_back'], new_back_int),
                )


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
    tangent = np.array([0, -1])
    inv_end = np.array([incl, width]) + tangent * edge._straight_len()

    inv_cps = deepcopy(cps)
    inv_cps[-1][1] *= -1  # Invert the last 

    inv_edge = pyp.CurveEdge(
        [incl, width], 
        inv_end.tolist(), 
        inv_cps
        )
    
    # Rotate by desired angle
    inv_edge.rotate(angle=-angle)  # TODO Angle

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
            pyp.utils.list_to_c(tangent),   # DRAFT curve_inv.unit_tangent(t=0) 
            pyp.utils.list_to_c(direction),  # DRAFT pyp.utils.list_to_c(np.array([-1 / np.sqrt(2), -1 / np.sqrt(2)])),  # DRAFT curve_inv.unit_tangent(t=1) 
        )
    )

    # DEBUG if not successfull.. etc.
    print(out)

    shift = out.x

    # DEBUG 
    print('Final shift for rotated curve')
    print(shift)

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

    # DEBUG
    print('Inverted Edge')
    print(edge)
    print(fin_inv_edge)

    return pyp.EdgeSequence(edge.reverse()), pyp.EdgeSequence(fin_inv_edge.reverse())


# TODO Move
def ArmholeOpeningEvening(front_opening, back_opening):
    """
        Rearrange sleeve openings for front and back s.t. we can costruct 
        two symmetric sleebe panels from them

        !! Important: assumes that the front opening is longer then back opening
    """

    # DEBUG
    print('Opening Rearrangements')

    # TODO special case when depth_front = depth_back

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
    intersect = np.array(pyp.c_to_list(target_segment.point(intersect_t)))


    # DEBUG
    connecting_point = np.array(front_opening[-1].end)
    print('Sleeve midpoint ', intersect)
    print('Sleeve diff ', np.linalg.norm(intersect - connecting_point))
    fsh, bsh = front_opening.shortcut(), back_opening.shortcut()
    print(
        'Shorthand before: ',
        np.linalg.norm(fsh[1] - fsh[0]), np.linalg.norm(bsh[1] - bsh[0])
    )

    # Update the opening shapes
    subdiv = front_opening.edges[-1].subdivide_param([intersect_t, 1 - intersect_t])
    front_opening.substitute(-1, subdiv[0])  # TODO connected correctly?

    # Move this part to the back opening
    subdiv[1].start, subdiv[1].end = copy(subdiv[1].start), copy(subdiv[1].end)  # Disconnect vertices in subdivided version
    subdiv.pop(0)   # TODO No reflect in the edge class??
    subdiv.reflect([0, 0], [1, 0]).reverse().snap_to(back_opening[-1].end)
    subdiv[0].start = back_opening[-1].end
    
    back_opening.append(subdiv[0])

    # DEBUG
    fsh, bsh = front_opening.shortcut(), back_opening.shortcut()
    print(
        'Shorthand after: ',
        np.linalg.norm(fsh[1] - fsh[0]), np.linalg.norm(bsh[1] - bsh[0])
    )


    # DEBUG matplotlib visuals for svgpathtools
    # points = (slope_midpoint, intersect)
    # plt.scatter(*zip(*points), color='blue', label="Intersect points")
    # st_int = slope_midpoint - 20 * slope_perp
    # end_int = slope_midpoint + 20 * slope_perp
    # plt.plot(
    #     [st_int[0], end_int[0]], 
    #     [st_int[1], end_int[1]],
    #     label='Inersect line'
    #     )
    # plt.plot(
    #     [slope[0][0], slope[1][0]], 
    #     [slope[0][1], slope[1][1]], 
    #     label="Slope")
    # plt.plot(
    #     [cfront[1].start[0], cfront[1].end[0]], 
    #     [cfront[1].start[1], cfront[1].end[1]], 
    #     label="Front line")

    # # # Add labels and legends
    # plt.xlabel("x-axis")
    # plt.ylabel("y-axis")
    # plt.xlim([-1, 60])
    # plt.ylim([-10, 30])
    # plt.legend()
    # plt.grid(True)

    # # Set the aspect ratio to be equal
    # plt.gca().set_aspect('equal', adjustable='box')

    # # Show the plot
    # plt.show()

    return front_opening, back_opening



# -------- New sleeve definitions -------

class ExperimentalSleevePanel(pyp.Panel):
    """Trying proper sleeve panel"""

    def __init__(self, name, body, design, open_shape):
        super().__init__(name)

        # TODO Standing sleeve
        # TODO end_width to be not less then the width of the arm??

        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        rest_angle = np.deg2rad(design['sleeve_angle']['v'])
        standing = design['standing_shoulder']['v']
        base_angle = max(rest_angle, shoulder_angle) # TODO if standing else shoulder_angle  # DEBUG Trying drape with smaller angle 

        length = design['length']['v']

        # Sleeve width with accounting for ruffles
        end_width = design['end_width']['v'] / 2 * design['end_ruffle']['v']
        if not pyp.utils.close_enough(design['connect_ruffle']['v'], 1):
            open_shape.extend(design['connect_ruffle']['v'])

        # Correct sleeve width -- after aligning rotation
        arm_width = abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # DEBUG
        print('Panel size: ', arm_width, end_width)

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

        # Interfaces
        self.interfaces = {
            # NOTE: interface needs reversing because the open_shape was reversed for construction
            'in': pyp.Interface(self, open_shape, ruffle=design['connect_ruffle']['v']),   # TODO .reverse(),
            'out': pyp.Interface(self, self.edges[0], ruffle=design['end_ruffle']['v']),
            'top': pyp.Interface(self, self.edges[1:3] if standing else self.edges[-1]),   # TODO relation for standing
            'bottom': pyp.Interface(self, self.edges[1])
        }

        # Default placement
        self.set_pivot(self.edges[1].end)
        self.translate_to(
            [- body['sholder_w'] / 2,
            body['height'] - body['head_l'] - body['armscye_depth'],
            0]) 
        self.rotate_to(R.from_euler('XYZ', [0, 0, body['arm_pose_angle']], degrees=True))


class ExperimentalSleeve(pyp.Component):
    """Trying to do a proper sleeve"""


    def __init__(self, tag, body, design, depth_diff=3) -> None:   # DEBUG
        super().__init__(f'{self.__class__.__name__}_{tag}')

        design = design['sleeve']
        inclanation = design['inclanation']['v']

        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        rest_angle = np.deg2rad(design['sleeve_angle']['v'])
        standing = design['standing_shoulder']['v']
        base_angle = rest_angle # DEBUG pose_angle if standing else shoulder_angle

        connecting_width = design['connecting_width']['v']
        smoothing_coeff = design['smoothing_coeff']['v']

        # Define sleeve opening shapes
        armhole = globals()[design['armhole_shape']['v']]
        front_project, front_opening = armhole(
            inclanation + depth_diff, connecting_width, 
            angle=base_angle, incl_coeff=smoothing_coeff, w_coeff=smoothing_coeff)
        
        back_project, back_opening = armhole(
            inclanation, connecting_width, 
            angle=base_angle, incl_coeff=smoothing_coeff, w_coeff=smoothing_coeff)

        if depth_diff != 0: 
            front_opening, back_opening = ArmholeOpeningEvening(
                front_opening, back_opening
            )

        # DEBUG
        print('Success!! ')
        print(front_project, back_project, front_opening, back_opening)

        # Get sleeve panels
        self.f_sleeve = ExperimentalSleevePanel(
            f'{tag}_sleeve_f', body, design, front_opening).translate_by(
                [-inclanation - depth_diff, 0, 25])
        self.b_sleeve = ExperimentalSleevePanel(
            f'{tag}_sleeve_b', body, design, back_opening).translate_by(
                [-inclanation, 0, -20])

        # DEBUG
        print('Stitch size matching')
        print(
            self.f_sleeve.interfaces['top'].edges.length(),
            self.b_sleeve.interfaces['top'].edges.length()
        )
        print(
            self.f_sleeve.interfaces['bottom'].edges.length(),
            self.b_sleeve.interfaces['bottom'].edges.length()
        )

        # Connect panels
        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces['top'], self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'], self.b_sleeve.interfaces['bottom']),
        )

        # Interfaces
        self.interfaces = {
            'in_front': self.f_sleeve.interfaces['in'].reverse(),
            'in_front_shape': pyp.Interface(self.f_sleeve, front_project),
            'in_back': self.b_sleeve.interfaces['in'],
            'in_back_shape': pyp.Interface(self.f_sleeve, back_project), 
            'in': pyp.Interface.from_multiple(
                self.f_sleeve.interfaces['in'].reverse(),
                self.b_sleeve.interfaces['in'].reverse()
            )
        }


        # TODO cuffs
