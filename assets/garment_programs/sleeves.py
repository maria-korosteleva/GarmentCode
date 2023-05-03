import numpy as np
from scipy.spatial.transform import Rotation as R
import svgpathtools as svgpath
from copy import copy

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
def ArmholeSquare(incl, width, angle=None, **kwargs):
    """Simple square armhole cut-out
        Not recommended to use for sleeves, stitching in 3D might be hard

        if angle is provided, it also calculated the shape of the sleeve interface to attach

        returns edge sequence and part to be preserved  inverted 
    """

    # DEBUG
    print('Creating square hole')
    print(incl, width)

    edges = pyp.esf.from_verts([0, 0], [incl, 0],  [incl, width])



    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyp.esf.from_verts(
        [incl + l*sina, - l*cosa], 
        [incl, 0],  [incl, width])

    return edges, sleeve_edges


def ArmholeSmooth(incl, width, angle=None, incl_coeff=0.2, w_coeff=0.2):
    """Piece-wise smooth armhole shape"""
    diff_incl = incl * (1 - incl_coeff)
    edges = pyp.esf.from_verts([0, 0], [diff_incl, w_coeff * width],  [incl, width])

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyp.esf.from_verts(
        [diff_incl + l*sina, w_coeff * width - l*cosa], 
        [diff_incl, w_coeff * width],  [incl, width])

    return edges, sleeve_edges


def line_intersection_with_segment(line, A, B):
    # ChatGPT-4
    m, c = line
    x1, y1 = A
    x2, y2 = B

    if x2 - x1 == 0:  # vertical segment
        x = x1
        y = m * x + c
    else:
        m1 = (y2 - y1) / (x2 - x1)
        c1 = y1 - m1 * x1

        if m == m1:
            return None  # parallel lines

        x = (c1 - c) / (m - m1)
        y = m * x + c

    if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
        return x, y
    else:
        return None  # intersection point is not within the segment


def ArmholeOpeningSquare(width, depth_front, depth_back, angle=None, **kwargs):
    """With calculated correct sleeve opening"""

    # DEBUG
    print('Creating ArmholeOpeningSquare')
    print(width, depth_front, depth_back)

    front_project, front_opening = ArmholeSquare(depth_front, width, angle=angle)
    back_project, back_opening = ArmholeSquare(depth_back, width, angle=angle)

    # TODO special case when depth_front = depth_back

    # Construct connected shape from opening inverses
    cfront, cback = front_opening.copy(), back_opening.copy()

    cback.reflect([0, 0], [1, 0]).reverse().snap_to(cfront[-1].end)

    slope = np.array([cfront[0].start, cback[-1].end])
    slope_vec = slope[1] - slope[0]
    slope_perp = np.asarray([-slope_vec[1], slope_vec[0]])
    slope_midpoint = (slope[0] + slope[1]) / 2

    # DRAFT 
    # # line equation for a perpendicular
    slope_m = -slope_vec[0] / slope_vec[1]

    # Intersection with the top line
    # svgpath tools allow solution regardless of egde types
    inter_segment = svgpath.Line(
        pyp.list_to_c(slope_midpoint - 20 * slope_perp), 
        pyp.list_to_c(slope_midpoint + 20 * slope_perp)
    )
    
    target_segment = cfront[1].as_curve()
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

    # Align the angle # TODO Figure out these alignements
    sl_angle = np.arctan(slope_m)
    front_opening.rotate(-sl_angle)  # TODO sign
    back_opening.rotate(sl_angle)


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

    return front_project, back_project, front_opening, back_opening


class ExperimentalSleevePanel(pyp.Panel):
    """Trying proper sleeve panel"""

    def __init__(self, name, body, design, open_shape):
        super().__init__(name)

        # TODO Standing sleeve
        # TODO ruffle
        # TODO end_width to be not less then the width of the arm??

        ease = 5  # TODO Parameter
        pose_angle = np.deg2rad(body['arm_pose_angle'])  # TODO Design parameter
        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        standing = design['standing_shoulder']['v']
        base_angle = pose_angle   # DEBUG if standing else shoulder_angle  # DEBUG Trying drape with smaller angle 

        length = design['length']['v']
        connecting_width =   design['connecting_width']['v'] + ease
        smoothing_coeff = design['smoothing_coeff']['v']

        end_width = design['end_width']['v'] / 2

        open_shape.rotate(-base_angle)   # TODO DEBUG
        # Correct sleeve width -- after aligning rotation
        arm_width = abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # DEBUG
        print('Panel size: ', arm_width, end_width)

        # Main body of a sleeve 
        top_length = length + connecting_width / np.tan(base_angle)  # DRAFT 
        self.edges = pyp.esf.from_verts(
            [0, 0], [0, -end_width], [length, -arm_width]
        )

        # Align the opening
        # TODO reverse might be needed
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)

        # DEBUG
        print('Total len ', self.edges.length())

        self.edges.close_loop()

        # DEBUG
        print('top_edge: ', self.edges[-1].length())

        # align the angle with the pose -- for draping
        self.edges.rotate(pose_angle) 

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


class ExperimentalSleeve(pyp.Component):
    """Trying to do a proper sleeve"""


    def __init__(self, tag, body, design, depth_diff=3) -> None:   # DEBUG
        super().__init__(f'{self.__class__.__name__}_{tag}')

        # DEBUG
        print(design.keys())

        design = design['sleeve']
        inclanation = design['inclanation']['v']

        pose_angle = np.deg2rad(body['arm_pose_angle'])
        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        standing = design['standing_shoulder']['v']
        base_angle = pose_angle if standing else shoulder_angle

        connecting_width = design['connecting_width']['v']
        smoothing_coeff = design['smoothing_coeff']['v']

        front_project, back_project, front_opening, back_opening = ArmholeOpeningSquare(
            connecting_width, inclanation + depth_diff, inclanation, angle=base_angle
        )

        # DEBUG
        print('Success!! ')
        print(front_project, back_project, front_opening, back_opening)

        # sleeves
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

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces['top'], self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'], self.b_sleeve.interfaces['bottom']),
        )

        # TODO Proper stitching 
        # (projections & openings do not correspond exactly anymore)

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
