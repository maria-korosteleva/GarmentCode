# Custom
import pypattern as pyp
import numpy as np
from scipy.spatial.transform import Rotation as R

# DRAFT
class SleevePanelOld(pyp.Panel):
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
        self.f_sleeve = SleevePanelOld(f'{tag}_f', body_opt, design_opt).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanelOld(f'{tag}_b', body_opt, design_opt).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces[0], self.b_sleeve.interfaces[0]),
            (self.f_sleeve.interfaces[2], self.b_sleeve.interfaces[2]),
        )

        self.interfaces = [
            self.f_sleeve.interfaces[1],
            self.b_sleeve.interfaces[1],
        ]


class SleeveOpeningPanelBack(pyp.Panel):
    def __init__(self, name, body, width, low_depth, top_depth) -> None:
        super().__init__(name)

        self.edges = pyp.esf.from_verts(
            [0, 0], [low_depth, 0],  [low_depth, width], 
            [low_depth - top_depth, width], 
            [low_depth * 0.2, 0.6 * width],
            loop=True)

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, self.edges[:2]),
            'shoulder': pyp.Interface(self, self.edges[2]),
            'out': pyp.Interface(self, self.edges[-1]),
        }

        # Default placement
        self.translate_to([-body['sholder_w'] / 2 - low_depth, body['height'] - body['head_l'] - body['armscye_depth'] + 4, 0])

class SleeveOpeningPanelFront(pyp.Panel):
    def __init__(self, name, body, width, low_depth, top_depth) -> None:
        super().__init__(name)

        self.edges = pyp.esf.from_verts(
            [0, 0], [low_depth, 0],  [low_depth, width], 
            [low_depth - top_depth, width], 
            [low_depth - top_depth, 0.2 * width], 
            loop=True)

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, self.edges[:2]),
            'shoulder': pyp.Interface(self, self.edges[2]),
            'out': pyp.Interface(self, self.edges[-1]),
        }

        # Default placement
        self.translate_to([-body['sholder_w'] / 2 - low_depth, body['height'] - body['head_l'] - body['armscye_depth'] + 4, 0])


class SleevePanel(pyp.Panel):
    def __init__(self, name, body, width, low_depth, top_depth) -> None:
        super().__init__(name)

        # TODO Cuffs, ruffles start, fulles end, opening shape..

        angle = np.deg2rad(50)
        sina, cosa = np.sin(angle), np.cos(angle)
        length = 30

        # Sleeve opening location
        bottom_v = [-length * sina, - length * cosa]
        delta_l = sina / cosa * (length * cosa + width) - low_depth + bottom_v[0]
        delta_y = delta_l * sina * cosa
        delta_x = delta_l * cosa * cosa


        self.edges = pyp.esf.from_verts(
            [0, 0], [length, 0], [length, low_depth],
            [length + width * cosa, low_depth + width * sina],
            [0, low_depth + width * sina],
            loop=True
        )
        # align the angle
        self.edges.rotate(angle)

        # DRAFT self.edges = pyp.esf.from_verts(
        #     [0, 0], [low_depth, 0],  [low_depth, width], 
        #     [low_depth - top_depth, width], 
        #     [bottom_v[0] - delta_x, bottom_v[1] + delta_y],
        #     [-length * sina, - length * cosa],
        #     loop=True)

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, self.edges[1:3]),
            'in_shape': pyp.Interface(self, pyp.esf.from_verts([0, 0], [low_depth, 0],  [low_depth, width])),
            # DRAFT 'shoulder': pyp.Interface(self, self.edges[2]),
            'out': pyp.Interface(self, self.edges[-1]),
            'top': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, self.edges[0])
        }

        # Default placement
        self.set_pivot(self.edges[0].end)
        self.translate_to([- body['sholder_w'] / 2 - low_depth, body['height'] - body['head_l'] - body['armscye_depth']+ 4, 0])


class SleeveStripPanel(pyp.Panel):
    def __init__(self, name, body, depth, length, angle) -> None:
        super().__init__(name)

        # TODO Cuffs, ruffles start, fulles end, opening shape..

        # Sleeve opening location
        self.edges = pyp.esf.from_verts(
            [0, 0], [length, 0], [length, depth], [0, depth],
            loop=True
        )
        # align the angle
        self.edges.rotate(angle)

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, self.edges[1:3]),
            'out': pyp.Interface(self, self.edges[-1]),
            'top': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, self.edges[0])
        }

        # Default placement
        self.set_pivot(self.edges[0].end)
        self.translate_to([- body['sholder_w'] / 2 - depth, body['height'] - body['head_l'] - body['armscye_depth']+ 4, 0])


class SleeveOpening(pyp.Component):

    def __init__(self, tag, body, inclanation, depth_diff) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        width = body['armscye_depth'] * 2
        
        # sleeves
        self.f_sleeve = SleevePanel(f'{tag}_f', body, width/2, inclanation + depth_diff, (inclanation + depth_diff) / 2).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(f'{tag}_b', body, width/2, inclanation, (inclanation + depth_diff) / 2).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            # DRAFT (self.f_sleeve.interfaces['shoulder'], self.b_sleeve.interfaces['shoulder']),
            (self.f_sleeve.interfaces['top'], self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'], self.b_sleeve.interfaces['bottom']),
        )

        self.interfaces = {
            'in_front': self.f_sleeve.interfaces['in'],
            'in_front_shape': pyp.Interface(self, pyp.esf.from_verts([0, 0], [inclanation, 0],  [inclanation, width])),
            'in_back': self.b_sleeve.interfaces['in'],
            'in_back_shape': self.b_sleeve.interfaces['in_shape'],
            'out': pyp.Interface.from_multiple(self.f_sleeve.interfaces['out'], self.b_sleeve.interfaces['out'])
        }


# DRAFT
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