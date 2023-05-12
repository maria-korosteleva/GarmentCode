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
    
    # TODOLOW Bend instead of rotating to avoid sharp connection
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
    # TODOLOW Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle) 

    return edges, sleeve_edges


def ArmholeCurve(incl, width, angle, **kwargs):
    """ Classic sleeve opening on Cubic Bezier curves
    """
    # Curvature as parameters?
    cps = [[0.5, 0.2], [0.8, 0.35]]
    edge = pyp.CurveEdge([incl, width], [0, 0], cps)

    # Initialize inverse (initial guess)
    # Agle == 0
    down_direction = np.array([0, -1])  # Full opening is vertically aligned
    inv_cps = deepcopy(cps)
    inv_cps[-1][1] *= -1  # Invert the last 
    inv_edge = pyp.CurveEdge(
        start=[incl, width], 
        end=(np.array([incl, width]) + down_direction * edge._straight_len()).tolist(), 
        control_points=inv_cps
    )

    # Rotate by desired angle (usually desired sleeve rest angle)
    inv_edge.rotate(angle=-angle)

    # Optimize the inverse shape to be nice
    shortcut = inv_edge.shortcut()
    rotated_direction = shortcut[-1] - shortcut[0]
    rotated_direction /= np.linalg.norm(rotated_direction)

    fin_inv_edge = pyp.ops.curve_match_tangents(
        inv_edge.as_curve(), 
        down_direction, 
        rotated_direction, 
        return_as_edge=True
    )

    return pyp.EdgeSequence(edge.reverse()), pyp.EdgeSequence(fin_inv_edge.reverse())


# -------- New sleeve definitions -------

class SleevePanel(pyp.Panel):
    """Trying proper sleeve panel"""

    def __init__(self, name, body, design, open_shape):
        super().__init__(name)

        # TODO end_width to be not less then the width of the arm??

        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        rest_angle = max(np.deg2rad(design['sleeve_angle']['v']), shoulder_angle)
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


class Sleeve(pyp.Component):
    """Trying to do a proper sleeve"""


    def __init__(self, tag, body, design, depth_diff=3) -> None: 
        super().__init__(f'{self.__class__.__name__}_{tag}')

        design = design['sleeve']
        inclanation = design['inclanation']['v']

        # TODOLOW Part of parameter processing
        rest_angle = max(np.deg2rad(design['sleeve_angle']['v']), np.deg2rad(body['shoulder_incl']))

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
            front_opening, back_opening = pyp.ops.even_armhole_openings(
                front_opening, back_opening
            )

        # Get sleeve panels
        self.f_sleeve = SleevePanel(
            f'{tag}_sleeve_f', body, design, front_opening).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(
            f'{tag}_sleeve_b', body, design, back_opening).translate_by([0, 0, -15])

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
            # Copy to avoid editing original design dict
            cdesign = deepcopy(design)
            cdesign['cuff']['b_width'] = design['end_width']

            cuff_class = getattr(bands, cdesign['cuff']['type']['v'])
            self.cuff = cuff_class(f'sl_{tag}', cdesign)

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
