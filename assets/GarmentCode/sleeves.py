# Custom
import pypattern as pyp
import numpy as np
from scipy.spatial.transform import Rotation as R

class SleevePanel(pyp.Panel):
    def __init__(self, name, body, design, width, low_depth, top_depth) -> None:
        super().__init__(name)

        # TODO Cuffs, ruffles start, fulles end, opening shape..

        angle = np.deg2rad(50)
        length = design['length']['v']
        armhole = globals()[design['armhole_shape']['v']]
        
        proj_shape, open_shape = armhole(low_depth, width, angle=angle, incl_coeff=0.2, w_coeff=0.1)

        open_shape.rotate(-angle)  
        arm_width = design['opening_width']['v'] / 2   # DRAFT  abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # Smoothing the top
        # FIXME Which doesn't work that effificently..
        self.edges = pyp.esf.from_verts(
            [0, 0], [0, -arm_width], [length, -arm_width]
        )
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)

        # align the angle
        self.edges.rotate(angle) 

        # top smooting 
        end = self.edges[-1].end
        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        len = design['shoulder_len']['v']
        self.edges.append(pyp.Edge(end, [end[0] - len * np.cos(shoulder_angle), end[1] - len * np.sin(shoulder_angle)]))

        # Fin
        self.edges.close_loop()
        

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, open_shape),
            'in_shape': pyp.Interface(self, proj_shape),
            'out': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[-2:]),   
            'bottom': pyp.Interface(self, self.edges[1])
        }

        # Default placement
        self.set_pivot(self.edges[-2].start)
        self.translate_to([- body['sholder_w'] / 2 - low_depth * 1.5, body['height'] - body['head_l'] + 4, 0])  #  - low_depth / 2


class Sleeve(pyp.Component):

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