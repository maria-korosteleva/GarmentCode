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
    def __init__(self, name, body, design, width, low_depth, top_depth) -> None:
        super().__init__(name)

        # TODO Cuffs, ruffles start, fulles end, opening shape..

        angle = np.deg2rad(50)
        length = design['length']['v']
        armhole = globals()[design['armhole_shape']['v']]
        
        proj_shape, open_shape = armhole(low_depth, width, angle=angle, incl_coeff=0.2, w_coeff=0.2)

        open_shape.rotate(-angle)  
        arm_width = abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # TODO add smooth angle on top

        self.edges = pyp.esf.from_verts(
            [0, 0], [0, -arm_width], [length, -arm_width]
        )
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)
        self.edges.close_loop()

        # align the angle
        self.edges.rotate(angle) 

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, open_shape),
            'in_shape': pyp.Interface(self, proj_shape),
            # DRAFT 'shoulder': pyp.Interface(self, self.edges[2]),
            'out': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[-1]),
            'bottom': pyp.Interface(self, self.edges[1])
        }

        # Default placement
        self.set_pivot(self.edges[-1].start)
        self.translate_to([- body['sholder_w'] / 2 - low_depth * 1.5, body['height'] - body['head_l'] + 4, 0])  #  - low_depth / 2


class SleeveOpening(pyp.Component):

    def __init__(self, tag, body, design, depth_diff) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        width = body['armscye_depth'] * 2
        design = design['sleeve']
        inclanation = design['inclanation']['v']
        
        # sleeves
        self.f_sleeve = SleevePanel(
            f'{tag}_f', body, design, 
            width/2, inclanation + depth_diff, (inclanation + depth_diff) / 2).translate_by([0, 0, 30])
        self.b_sleeve = SleevePanel(
            f'{tag}_b', body, design, 
            width/2, inclanation, (inclanation + depth_diff) / 2).translate_by([0, 0, -25])

        self.stitching_rules = pyp.Stitches(
            # DRAFT (self.f_sleeve.interfaces['shoulder'], self.b_sleeve.interfaces['shoulder']),
            (self.f_sleeve.interfaces['top'], self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'], self.b_sleeve.interfaces['bottom']),
        )

        self.interfaces = {
            'in_front': self.f_sleeve.interfaces['in'],
            'in_front_shape': self.f_sleeve.interfaces['in_shape'],
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



# ------  Armhole shapes ------
def ArmholeSquare(incl, width, angle=None, **kwargs):
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