import numpy as np
from scipy.spatial.transform import Rotation as R

# Custom
import pypattern as pyp
from . import bands


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

        open_shape.reverse()  # TODO CHECK if needed

        if not pyp.utils.close_enough(design['connect_ruffle']['v'], 1):
            open_shape.extend(design['connect_ruffle']['v'])

        open_shape.rotate(-base_angle)  

        # TODO end ruffle may need to extend in both direction instead
        # DEBUG arm_width = (design['end_width']['v'] + width_diff) / 2  * design['end_ruffle']['v']
        arm_width = abs(open_shape[0].start[1] - open_shape[-1].end[1])

        # Main body of a sleeve
        self.edges = pyp.esf.from_verts(
            [0, 0], [0, arm_width], [length, arm_width]
        )
        
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)

        # align the angle with the pose -- for draping
        self.edges.rotate(pose_angle) 

        # FIXME Update standing sholder with a new formulation
        if standing:  # Add a "shelve" to create square shoulder appearance
            end = self.edges[-1].end
            len = design['standing_shoulder_len']['v']
            self.edges.append(pyp.Edge(
                end, [end[0] - len * np.cos(shoulder_angle), end[1] - len * np.sin(shoulder_angle)]))

        # Fin
        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, open_shape, ruffle=design['connect_ruffle']['v']),
            'in_shape': pyp.Interface(self, proj_shape),
            'out': pyp.Interface(self, self.edges[0], ruffle=design['end_ruffle']['v']),
            'top': pyp.Interface(self, self.edges[1:3] if standing else self.edges[1]),   
            'bottom': pyp.Interface(self, self.edges[-1])
        }

        # Default placement
        self.set_pivot(self.edges[1].end)
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
            self.cuff = cuff_class(tag, design)
            cbbox = self.cuff.bbox3D()

            # Position
            # TODO positioning is still not very robust
            pose_angle = np.deg2rad(body['arm_pose_angle'])
            self.cuff.rotate_by(R.from_euler('XYZ', [0, 0, -pose_angle]))
            self.cuff.translate_by([
                bbox[0][0] + (cbbox[0][0] + cbbox[1][0]) / 2 + 13 * np.cos(pose_angle),
                bbox[0][1] + 8 * np.sin(pose_angle), 
                0
            ])

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