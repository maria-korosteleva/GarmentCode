import numpy as np
from scipy.spatial.transform import Rotation as R

import pygarment as pyg

from assets.garment_programs.bands import StraightBandPanel
from assets.garment_programs.circle_skirt import CircleArcPanel


# # ------ Collar shapes withough extra panels ------

def VNeckHalf(depth, width, **kwargs):
    """Simple VNeck design"""

    edges = pyg.EdgeSequence(pyg.Edge([0, 0], [width / 2, -depth]))
    return edges

def SquareNeckHalf(depth, width, **kwargs):
    """Square design"""

    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    return edges

def TrapezoidNeckHalf(depth, width, angle=90, verbose=True, **kwargs):
    """Trapesoid neck design"""

    # Special case when angle = 180 (sin = 0)
    if (pyg.utils.close_enough(angle, 180, tol=1) 
            or pyg.utils.close_enough(angle, 0, tol=1)):
        # degrades into VNeck
        return VNeckHalf(depth, width)

    rad_angle = np.deg2rad(angle)

    bottom_x = -depth * np.cos(rad_angle) / np.sin(rad_angle)
    if bottom_x > width / 2:  # Invalid angle/depth/width combination resulted in invalid shape
        if verbose:
            print('TrapezoidNeckHalf::WARNING::Parameters are invalid and create overlap: '
                  f'{bottom_x} > {width / 2}. '
                  'The collar is reverted to VNeck')

        return VNeckHalf(depth, width)

    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [bottom_x, -depth], [width / 2, -depth])
    return edges

def CurvyNeckHalf(depth, width, flip=False, **kwargs):
    """Testing Curvy Collar design"""

    sign = -1 if flip else 1
    edges = pyg.EdgeSequence(pyg.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[0.4, sign * 0.3], [0.8, sign * -0.3]]))
    
    return edges

def CircleArcNeckHalf(depth, width, angle=90, flip=False, **kwargs):
    """Collar with a side represented by a circle arc"""
    # 1/4 of a circle
    edges = pyg.EdgeSequence(pyg.CircleEdgeFactory.from_points_angle(
        [0, 0], [width / 2,-depth], arc_angle=np.deg2rad(angle),
        right=(not flip)
    ))

    return edges


def CircleNeckHalf(depth, width, **kwargs):
    """Collar that forms a perfect circle arc when halfs are stitched"""

    # Take a full desired arc and half it!
    circle = pyg.CircleEdgeFactory.from_three_points(
        [0, 0],
        [width, 0],
        [width / 2, -depth])
    subdiv = circle.subdivide_len([0.5, 0.5])
    return pyg.EdgeSequence(subdiv[0])

def Bezier2NeckHalf(depth, width, flip=False, x=0.5, y=0.3, **kwargs):
    """2d degree Bezier curve as neckline"""

    sign = 1 if flip else -1
    edges = pyg.EdgeSequence(pyg.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[x, sign*y]]))
    
    return edges

# # ------ Collars with panels ------

class NoPanelsCollar(pyg.Component):
    """Face collar class that only forms the projected shapes """
    
    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # Front
        collar_type = globals()[design['collar']['f_collar']['v']]
        f_collar = collar_type(
            design['collar']['fc_depth']['v'],
            design['collar']['width']['v'], 
            angle=design['collar']['fc_angle']['v'], 
            flip=design['collar']['f_flip_curve']['v'],
            x=design['collar']['f_bezier_x']['v'],
            y=design['collar']['f_bezier_y']['v'],
            verbose=self.verbose
        )

        # Back
        collar_type = globals()[design['collar']['b_collar']['v']]
        b_collar = collar_type(
            design['collar']['bc_depth']['v'], 
            design['collar']['width']['v'], 
            angle=design['collar']['bc_angle']['v'],
            flip=design['collar']['b_flip_curve']['v'],
            x=design['collar']['b_bezier_x']['v'],
            y=design['collar']['b_bezier_y']['v'],
            verbose=self.verbose
        )
        
        self.interfaces = {
            'front_proj': pyg.Interface(self, f_collar),
            'back_proj': pyg.Interface(self, b_collar)
        }
    
    def length(self):
        return 0


class Turtle(pyg.Component):

    def __init__(self, tag, body, design) -> None:
        super().__init__(f'Turtle_{tag}')

        depth = design['collar']['component']['depth']['v']

        # --Projecting shapes--
        f_collar = CircleNeckHalf(
            design['collar']['fc_depth']['v'],
            design['collar']['width']['v'])
        b_collar = CircleNeckHalf(
            design['collar']['bc_depth']['v'],
            design['collar']['width']['v'])
        
        self.interfaces = {
            'front_proj': pyg.Interface(self, f_collar),
            'back_proj': pyg.Interface(self, b_collar)
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body['height'] - body['head_l'] + depth

        self.front = StraightBandPanel(
            f'{tag}_collar_front', length_f, depth).translate_by(
            [-length_f / 2, height_p, 10])
        self.back = StraightBandPanel(
            f'{tag}_collar_back', length_b, depth).translate_by(
            [-length_b / 2, height_p, -10])

        self.stitching_rules.append((
            self.front.interfaces['right'], 
            self.back.interfaces['right']
        ))

        self.interfaces.update({
            'front': self.front.interfaces['left'],
            'back': self.back.interfaces['left'],
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'],
                self.back.interfaces['bottom']
            )
        })

    def length(self):
        return self.interfaces['back'].edges.length()


class SimpleLapelPanel(pyg.Panel):
    """A panel for the front part of simple Lapel"""
    def __init__(self, name, length, max_depth) -> None:
        super().__init__(name)

        self.edges = pyg.EdgeSeqFactory.from_verts(
            [0, 0], [max_depth, 0], [max_depth, -length]
        )

        self.edges.append(
            pyg.CurveEdge(
                self.edges[-1].end, 
                self.edges[0].start, 
                [[0.7, 0.2]]
            )
        )

        self.interfaces = {
            'to_collar': pyg.Interface(self, self.edges[0]),
            'to_bodice': pyg.Interface(self, self.edges[1])
        }


class SimpleLapel(pyg.Component):

    def __init__(self, tag, body, design) -> None:
        super().__init__(f'Turtle_{tag}')

        depth = design['collar']['component']['depth']['v']
        standing = design['collar']['component']['lapel_standing']['v']

        # --Projecting shapes--
        # Any front one!
        collar_type = globals()[design['collar']['f_collar']['v']]
        f_collar = collar_type(
            design['collar']['fc_depth']['v'],
            design['collar']['width']['v'], 
            angle=design['collar']['fc_angle']['v'], 
            flip=design['collar']['f_flip_curve']['v'])
        
        b_collar = CircleNeckHalf(
            design['collar']['bc_depth']['v'],
            design['collar']['width']['v'])
        
        self.interfaces = {
            'front_proj': pyg.Interface(self, f_collar),
            'back_proj': pyg.Interface(self, b_collar)
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body['height'] - body['head_l'] + depth * 2
        
        self.front = SimpleLapelPanel(
            f'{tag}_collar_front', length_f, depth).translate_by(
            [-depth * 2, height_p, 35])  # FIXME This should be related with the bodice panels' placement

        if standing:
            self.back = StraightBandPanel(
                f'{tag}_collar_back', length_b, depth).translate_by(
                [-length_b / 2, height_p, -10])
        else:
            # A curved back panel that follows the collar opening
            rad, angle, _ = b_collar[0].as_radius_angle()
            self.back = CircleArcPanel(
                f'{tag}_collar_back', rad, depth, angle  
            ).translate_by([-length_b, height_p, -10])
            self.back.rotate_by(R.from_euler('XYZ', [90, 45, 0], degrees=True))

        if standing:
            self.back.interfaces['right'].set_right_wrong(True)

        self.stitching_rules.append((
            self.front.interfaces['to_collar'], 
            self.back.interfaces['right']
        ))

        self.interfaces.update({
            #'front': NOTE: no front interface here
            'back': self.back.interfaces['left'],
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['to_bodice'].set_right_wrong(True),
                self.back.interfaces['bottom'] if standing else self.back.interfaces['top'].set_right_wrong(True),
            )
        })

    def length(self):
        return self.interfaces['back'].edges.length()

class HoodPanel(pyg.Panel):
    """A panel for the side of the hood"""
    def __init__(self, name, f_depth, b_depth, f_length, b_length, width, in_length, depth) -> None:
        super().__init__(name)

        width = width / 2  # Panel covers one half only
        length = in_length + width / 2  

        # Bottom-back
        bottom_back_in = pyg.CurveEdge(
            [-width, -b_depth], 
            [0, 0],
            [[0.3, -0.2], [0.6, 0.2]]
        )
        bottom_back = pyg.ops.curve_match_tangents(
            bottom_back_in.as_curve(), 
            [1, 0],  # Full opening is vertically aligned
            [1, 0],
            target_len=b_length,
            return_as_edge=True, 
            verbose=self.verbose
        )
        self.edges.append(bottom_back)

        # Bottom front
        bottom_front_in = pyg.CurveEdge(
            self.edges[-1].end, 
            [width, -f_depth],
            [[0.3, 0.2], [0.6, -0.2]]
        )
        bottom_front = pyg.ops.curve_match_tangents(
            bottom_front_in.as_curve(), 
            [1, 0],  # Full opening is vertically aligned
            [1, 0],
            target_len=f_length,
            return_as_edge=True,
            verbose=self.verbose
        )
        self.edges.append(bottom_front)

        # Front-top straight section 
        self.edges.append(pyg.EdgeSeqFactory.from_verts(
            self.edges[-1].end,
            [width * 1.2, length], [width * 1.2 - depth, length]
        ))
        # Back of the hood
        self.edges.append(
            pyg.CurveEdge(
                self.edges[-1].end, 
                self.edges[0].start, 
                [[0.2, -0.5]]
            )
        )

        self.interfaces = {
            'to_other_side': pyg.Interface(self, self.edges[-2:]),
            'to_bodice': pyg.Interface(self, self.edges[0:2]).reverse()
        }

        self.rotate_by(R.from_euler('XYZ', [0, -90, 0], degrees=True))
        self.translate_by([-width, 0, 0])

class Hood2Panels(pyg.Component):

    def __init__(self, tag, body, design) -> None:
        super().__init__(f'Hood_{tag}')

        # --Projecting shapes--
        width = design['collar']['width']['v']
        f_collar = CircleNeckHalf(
            design['collar']['fc_depth']['v'],   
            design['collar']['width']['v'])
        b_collar = CircleNeckHalf(
            design['collar']['bc_depth']['v'],   
            design['collar']['width']['v'])
        
        self.interfaces = {
            'front_proj': pyg.Interface(self, f_collar),
            'back_proj': pyg.Interface(self, b_collar)
        }

        # -- Panel --
        self.panel = HoodPanel(
            f'{tag}_hood', 
            design['collar']['fc_depth']['v'],
            design['collar']['bc_depth']['v'],
            f_length=f_collar.length(),
            b_length=b_collar.length(),
            width=width,
            in_length=body['head_l'] * design['collar']['component']['hood_length']['v'],
            depth=width / 2 * design['collar']['component']['hood_depth']['v']
        ).translate_by(
            [0, body['height'] - body['head_l'] + 10, 0])

        self.interfaces.update({
            #'front': NOTE: no front interface here
            'back': self.panel.interfaces['to_other_side'],
            'bottom': self.panel.interfaces['to_bodice']
        })

    def length(self):
        return self.panel.length()

