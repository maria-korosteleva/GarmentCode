import numpy as np
from scipy.spatial.transform import Rotation as R

import pypattern as pyp

from assets.garment_programs.bands import StraightBandPanel
from assets.garment_programs.circle_skirt import CircleArcPanel


# # ------ Collar shapes withough extra panels ------

def VNeckHalf(depth, width, **kwargs):
    """Simple VNeck design"""

    edges = pyp.EdgeSequence(pyp.Edge([0, 0], [width / 2, -depth]))
    return edges

def SquareNeckHalf(depth, width, **kwargs):
    """Square design"""

    edges = pyp.EdgeSeqFactory.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    return edges

def TrapezoidNeckHalf(depth, width, angle=90, verbose=True, **kwargs):
    """Trapesoid neck design"""

    # Special case when angle = 180 (sin = 0)
    if (pyp.utils.close_enough(angle, 180, tol=1) 
            or pyp.utils.close_enough(angle, 0, tol=1)):
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

    edges = pyp.EdgeSeqFactory.from_verts([0, 0], [bottom_x, -depth], [width / 2, -depth])
    return edges

def CurvyNeckHalf(depth, width, flip=False, **kwargs):
    """Testing Curvy Collar design"""

    sign = -1 if flip else 1
    edges = pyp.EdgeSequence(pyp.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[0.4, sign * 0.3], [0.8, sign * -0.3]]))
    
    return edges

def CircleArcNeckHalf(depth, width, angle=90, flip=False, **kwargs):
    """Collar with a side represented by a circle arc"""
    # 1/4 of a circle
    edges = pyp.EdgeSequence(pyp.CircleEdgeFactory.from_points_angle(
        [0, 0], [width / 2,-depth], arc_angle=np.deg2rad(angle),
        right=(not flip)
    ))

    return edges


def CircleNeckHalf(depth, width, **kwargs):
    """Collar that forms a perfect circle arc when halfs are stitched"""

    # Take a full desired arc and half it!
    circle = pyp.CircleEdgeFactory.from_three_points(
        [0, 0],
        [width, 0],
        [width / 2, -depth])
    subdiv = circle.subdivide_len([0.5, 0.5])
    return pyp.EdgeSequence(subdiv[0])

def Bezier2NeckHalf(depth, width, flip=False, x=0.5, y=0.3, **kwargs):
    """2d degree Bezier curve as neckline"""

    sign = 1 if flip else -1
    edges = pyp.EdgeSequence(pyp.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[x, sign*y]]))
    
    return edges

# # ------ Collars with panels ------

class NoPanelsCollar(pyp.Component):
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
            y=design['collar']['f_bezier_y']['v'],)

        # Back
        collar_type = globals()[design['collar']['b_collar']['v']]
        b_collar = collar_type(
            design['collar']['bc_depth']['v'], 
            design['collar']['width']['v'], 
            angle=design['collar']['bc_angle']['v'],
            flip=design['collar']['b_flip_curve']['v'],
            x=design['collar']['b_bezier_x']['v'],
            y=design['collar']['b_bezier_y']['v'],
            )
        
        self.interfaces = {
            'front_proj': pyp.Interface(self, f_collar),
            'back_proj': pyp.Interface(self, b_collar)
        }


class Turtle(pyp.Component):

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
            'front_proj': pyp.Interface(self, f_collar),
            'back_proj': pyp.Interface(self, b_collar)
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
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'],
                self.back.interfaces['bottom']
            )
        })


class SimpleLapelPanel(pyp.Panel):
    """A panel for the front part of simple Lapel"""
    def __init__(self, name, length, max_depth) -> None:
        super().__init__(name)

        self.edges = pyp.EdgeSeqFactory.from_verts(
            [0, 0], [max_depth, 0], [max_depth, -length]
        )

        self.edges.append(
            pyp.CurveEdge(
                self.edges[-1].end, 
                self.edges[0].start, 
                [[0.7, 0.2]]
            )
        )

        self.interfaces = {
            'to_collar': pyp.Interface(self, self.edges[0]),
            'to_bodice': pyp.Interface(self, self.edges[1])
        }


class SimpleLapel(pyp.Component):

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
            'front_proj': pyp.Interface(self, f_collar),
            'back_proj': pyp.Interface(self, b_collar)
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body['height'] - body['head_l'] + depth * 2
        
        self.front = SimpleLapelPanel(
            f'{tag}_collar_front', length_f, depth).translate_by(
            [-depth * 2, height_p, 30])

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

        self.stitching_rules.append((
            self.front.interfaces['to_collar'], 
            self.back.interfaces['right']
        ))

        self.interfaces.update({
            #'front': NOTE: no front interface here
            'back': self.back.interfaces['left'],
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['to_bodice'],
                self.back.interfaces['bottom'] if standing else self.back.interfaces['top'],
            )
        })


class HoodPanel(pyp.Panel):
    """A panel for the side of the hood"""
    def __init__(self, name, f_depth, b_depth, width, in_length, depth) -> None:
        super().__init__(name)

        width = width / 2  # Panel covers one half only
        length = in_length + width / 2    # DRAFT np.sqrt(in_length**2 + width**2)  # Account for "flattening" in the neck area

        # DEBUG
        print(in_length, length, width, in_length**2 + width**2)

        self.edges = pyp.EdgeSeqFactory.from_verts(
            [-width, -b_depth], [0, 0], [width, -f_depth], [width * 1.2, length], [width * 1.2 - depth, length]
        )
        self.edges.append(
            pyp.CurveEdge(
                self.edges[-1].end, 
                self.edges[0].start, 
                [[0.2, -0.5]]
            )
        )

        self.interfaces = {
            'to_other_side': pyp.Interface(self, self.edges[-2:]),
            'to_bodice': pyp.Interface(self, self.edges[0:2]).reverse()
        }

        self.rotate_by(R.from_euler('XYZ', [0, -90, 0], degrees=True))
        self.translate_by([-width * 1.5, 0, 0])

class Hood2Panels(pyp.Component):

    def __init__(self, tag, body, design) -> None:
        super().__init__(f'Hood_{tag}')

        depth = design['collar']['component']['depth']['v'] 

        # TODO circle back
        # TODO arbitraty front? 
        # TODO design parameters

        # --Projecting shapes--
        # DRAFT 
        # Any front one!
        # collar_type = globals()[design['collar']['f_collar']['v']]
        # 
        # f_collar = collar_type(
        #     design['collar']['fc_depth']['v'],
        #     design['collar']['width']['v'], 
        #     angle=design['collar']['fc_angle']['v'], 
        #     flip=design['collar']['f_flip_curve']['v'])
        
        # b_collar = CircleNeckHalf(
        #     design['collar']['bc_depth']['v'],
        #     design['collar']['width']['v'])

        width = design['collar']['width']['v']
        f_collar = VNeckHalf(
            design['collar']['fc_depth']['v'],
            width)
        b_collar = VNeckHalf(
            design['collar']['bc_depth']['v'],
            width)
        
        self.interfaces = {
            'front_proj': pyp.Interface(self, f_collar),
            'back_proj': pyp.Interface(self, b_collar)
        }

        # -- Panel --
        length_f, length_b = f_collar.length(), b_collar.length()
        
        self.panel = HoodPanel(
            f'{tag}_hood', 
            design['collar']['fc_depth']['v'],
            design['collar']['bc_depth']['v'],
            width,
            body['head_l'], # DRAFT + body['neck_w'] / 2,  # DRAFT  * 1.4,  # TODOLOW It would be better to use head width measurement
            depth=width / 2
        ).translate_by(
            [0, body['height'] - body['head_l'] + 10, 0])

        self.interfaces.update({
            #'front': NOTE: no front interface here
            'back': self.panel.interfaces['to_other_side'],
            'bottom': self.panel.interfaces['to_bodice']
        })


