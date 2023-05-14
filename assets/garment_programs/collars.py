import numpy as np
from scipy.spatial.transform import Rotation as R

# Custom
import pypattern as pyp

# Other assets

from .bands import BandPanel


# Collar shapes withough extra panels
def VNeckHalf(depth, width, **kwargs):
    """Simple VNeck design"""

    edges = pyp.EdgeSequence(pyp.Edge([0, 0], [width / 2,-depth]))
    
    return edges


def SquareNeckHalf(depth, width, **kwargs):
    """Square design"""

    edges = pyp.esf.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    
    return edges

def TrapezoidNeckHalf(depth, width, angle=90, **kwargs):
    """Trapesoid neck design"""

    # Special case when angle = 180 (sin = 0)
    if (pyp.utils.close_enough(angle, 180, tol=1) 
            or pyp.utils.close_enough(angle, 0, tol=1)):
        # degrades into VNeck
        return VNeckHalf(depth, width)

    angle = np.deg2rad(angle)

    edges = pyp.esf.from_verts([0, 0], [-depth * np.cos(angle) / np.sin(angle), -depth], [width / 2, -depth])

    return edges


# Collar shapes withough extra panels
def CurvyNeckHalf(depth, width, **kwargs):
    """Testing Curvy Collar design"""

    edges = pyp.EdgeSequence(pyp.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[0.4, 0.3], [0.8, -0.5]]))
    
    return edges


def CircleArcNeckHalf(depth, width, angle=90, **kwargs):
    """Collar with a side represented by a circle arc"""
    # 1/4 of a circle
    edges = pyp.EdgeSequence(pyp.CircleEdge.from_points_angle(
        [0, 0], [width / 2,-depth], arc_angle=np.deg2rad(angle),
        right=True
    ))

    return edges

def CircleNeckHalf(depth, width, **kwargs):
    """Collar that forms a perfect circle arc when halfs are stitched"""

    # Take a full desired arc and half it!
    circle = pyp.CircleEdge.from_three_points([0, 0], [width, 0], [width / 2, -depth])

    subdiv = circle.subdivide_len([0.5, 0.5])

    return pyp.EdgeSequence(subdiv[0])


# # ------ Collars with panels ------

class Turtle(pyp.Component):

    def __init__(self, tag, body, design, length_f, length_b) -> None:
        super().__init__(f'Turtle_{tag}')

        depth = design['style_depth']['v']

        height_p = body['height'] - body['head_l'] + depth * 2
        self.front = BandPanel(
            f'{tag}_turtle_front', length_f, depth).translate_by([-length_f / 2, height_p, 10])
        self.back = BandPanel(
            f'{tag}_turtle_back', length_b, depth).translate_by([-length_b / 2, height_p, -10])

        self.stitching_rules.append((
            self.front.interfaces['left'], 
            self.back.interfaces['left']
        ))

        self.interfaces = {
            'front': self.front.interfaces['right'],
            'back': self.back.interfaces['right'],
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'],
                self.back.interfaces['bottom'],
            )
        }

        # DRAFT self.panel.top_center_pivot()
        # self.translate_to(
        #     [
        #         -body['neck_w'] / 2, 
        #         body['height'] - body['head_l'] + depth * 2, 
        #         0
        #     ]
        # )
        # self.rotate_by(R.from_euler('XYZ', [0, 90, 0], True))  # TODO rotation sign?


# DRAFT
# class TurtleNeckHalf(pyp.Component):
#     """Classic Turtleneck"""

#     def __init__(self, body, design) -> None:
#         super().__init__('TurtleNeck')

#         design = design['collar']

#         # Collar depth is given w.r.t. length.
#         # adjust for the shoulder inclination
#         width = design['collar']['width']['v']
#         tg = np.tan(np.deg2rad(body['shoulder_incl']))
#         f_depth_adj = tg * (self.ftorso.width - width / 2)
#         b_depth_adj = tg * (self.btorso.width - width / 2)

#         # Front
#         collar_type = globals()[design['collar']['f_collar']['v']]
#         f_collar = collar_type(
#             design['collar']['fc_depth']['v'] + f_depth_adj, 
#             width, 
#             angle=design['collar']['fc_angle']['v'])
#         pyp.ops.cut_corner(f_collar, self.ftorso.interfaces['collar_corner'])

#         # Back
#         collar_type = getattr(collars, design['collar']['b_collar']['v'])
#         b_collar = collar_type(
#             design['collar']['bc_depth']['v'] + b_depth_adj, 
#             width, 
#             angle=design['collar']['bc_angle']['v'])
#         pyp.ops.cut_corner(b_collar, self.btorso.interfaces['collar_corner'])

#         # Panels
#         self.panel = BandPanel()

#         # Connect

#         # Projected shape

#         # TODO Use collars with panels in Bodice block

#         # TODO Combine with strapless option for cool effect!




