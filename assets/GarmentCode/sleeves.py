# Custom
import pypattern as pyp
import numpy as np
from scipy.spatial.transform import Rotation as R

# DRAFT
class SleevePanel(pyp.Panel):
    """Simple panel for a sleeve with optional ruffles on the sholder connection"""

    def __init__(self, name, body_opt, design_opt) -> None:
        super().__init__(name)

        arm_width = body_opt['arm_width']
        length = design_opt['sleeve']['length']['v']
        ease = design_opt['sleeve']['ease']['v']
        ruffle = design_opt['sleeve']['ruffle']['v']
        incl = design_opt['sleeve']['inclanation']['v']

        width = ruffle * (arm_width + ease) / 2 
        self.edges = pyp.esf.from_verts([0, 0], [0, width], [length, width], [length - incl, 0], loop=True)

        # default placement
        self.translate_by([-length - 20, 15, 0])

        self.interfaces = [
            pyp.Interface(self, self.edges[1]),
            pyp.Interface(self, self.edges[2], ruffle=ruffle),
            pyp.Interface(self, self.edges[3]),
        ]

class SimpleSleeve(pyp.Component):
    """Very simple sleeve"""
    def __init__(self, tag, body_opt, design_opt) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        # sleeves
        self.f_sleeve = SleevePanel(f'{tag}_f', body_opt, design_opt).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(f'{tag}_b', body_opt, design_opt).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces[0], self.b_sleeve.interfaces[0]),
            (self.f_sleeve.interfaces[2], self.b_sleeve.interfaces[2]),
        )

        self.interfaces = [
            self.f_sleeve.interfaces[1],
            self.b_sleeve.interfaces[1],
        ]


class SleeveSquareOpening(pyp.Panel):
    """Basic sleeve implementation with proper fitting"""
    def __init__(self, tag, body, inclanation, width_shift, depth_diff) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        # TODO No width_shift needed

        width = body['armscye_depth'] * 2
        b_width = width / 2 - width_shift

        b_depth, f_depth = inclanation, inclanation + depth_diff

        self.edges = pyp.esf.from_verts(
            [0, 0], [0, b_depth], [b_width, b_depth], [width, b_depth], [width, -depth_diff],
            loop=True
            )

        print(self.edges)  # DEBUG

        # Projection shape onto front & back panels 
        front_cut = self.edges[2:4].copy().snap_to([0, 0])
        print('Front cut before rot: ', front_cut) # DEBUG
        front_cut.rotate(-np.pi / 2).reverse().snap_to([0, 0])
        print('Front cut after rot: ', front_cut, '\n') # DEBUG

        back_cut = self.edges[:2].copy()
        print('Back cut before rot: ', back_cut)  # DEBUG
        back_cut.rotate(np.pi / 2).reflect([0, 0], [0, 1])
        print('Back cut after rot: ', back_cut, '\n') # DEBUG

        # Interfaces
        self.interfaces = {
            'in_front': pyp.Interface(self, self.edges[2:4]),
            'in_back': pyp.Interface(self, self.edges[:2]),
            'front_cut': pyp.Interface(self, front_cut),
            'back_cut': pyp.Interface(self, back_cut),
            'out': pyp.Interface(self, self.edges[-1]),
        }

        # Default placement
        self.rotate_to(R.from_euler('XYZ', [-90, -90, 0], degrees=True))
        self.translate_to([-body['sholder_w'] / 2 - 4, body['waist_line'] + 4, - width / 2])



# Armhole shapes withough sleeves
# TODO I need here the matching interface for interchengeability ..
def ArmholeSimple(tag, body, design):
    arm_width = body['arm_width']
    ease = design['sleeve']['ease']['v'] 
    incl = design['sleeve']['inclanation']['v']
    width = (arm_width + ease) / 2

    edges_front = pyp.EdgeSequence(pyp.Edge([0, 0], [incl, width]))
    edges_back = pyp.EdgeSequence(pyp.Edge([0, 0], [incl, width]))
    
    return edges_front, edges_back

# TODO parameters are a bit stupid
def ArmholeSquare(tag, body, design, shift, incl):
    arm_width = body['arm_width']
    ease = design['sleeve']['ease']['v'] 
    # DRAFT incl = design['sleeve']['inclanation']['v']
    width = (arm_width + ease) / 2

    edges_front = pyp.esf.from_verts([0, 0], [incl, 0],  [incl, width + shift])
    edges_back = pyp.esf.from_verts([0, 0], [incl, 0],  [incl, width - shift])
    
    return edges_front, edges_back


def ArmholeSquareSide(tag, body, design, shift, incl):
    arm_width = body['arm_width']
    ease = design['sleeve']['ease']['v'] 
    # DRAFT incl = design['sleeve']['inclanation']['v']
    width = (arm_width + ease) / 2

    edges = pyp.esf.from_verts([0, 0], [incl, 0],  [incl, width + shift])
    
    return edges