# Custom
import pypattern as pyp
import numpy as np
from scipy.spatial.transform import Rotation as R

class SleevePanel(pyp.Panel):
    def __init__(self, name, body, design, 
        proj_shape, open_shape, opening_depth, end_width) -> None:
        """Extra parameters are needed to calculate the shapes for front and back sleeves correctly
            (they are slightly different, but overall calculation process is the same)
        """
        super().__init__(name)

        # TODO Cuffs, ruffles start, fulles end, opening shape..

        connecting_depth = design['connecting_depth']['v']
        length = design['length']['v']

        pose_angle = np.deg2rad(body['arm_pose_angle'])
        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        standing = design['standing_shoulder']['v']

        base_angle = pose_angle if standing else shoulder_angle

        # DEBUG
        print('\n', self.name)
        print(proj_shape.length(), proj_shape.shortcut_length())
        print(open_shape.length(), open_shape.shortcut_length())

        open_shape.rotate(-base_angle)  
        
        # DRAFT end_width = (design['end_width']['v'] + width_diff) / 2 

        # Main body of a sleeve
        self.edges = pyp.esf.from_verts(
            [0, 0], [0, -end_width], [length, -end_width]
        )
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)

        print(self.edges)  # DEBUG
        print(self.edges.lengths())

        # align the angle with the pose -- for draping
        self.edges.rotate(pose_angle) 

        if standing:  # Add a "shelve" to create square shoulder appearance
            end = self.edges[-1].end
            len = design['standing_shoulder_len']['v']
            self.edges.append(pyp.Edge(
                end, 
                [end[0] - len * np.cos(shoulder_angle), end[1] - len * np.sin(shoulder_angle)]))

        # Fin
        self.edges.close_loop()
        
        # Interfaces
        self.interfaces = {
            'in': pyp.Interface(self, open_shape),
            'in_shape': pyp.Interface(self, proj_shape),
            'out': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[-2:] if standing else self.edges[-1]),   
            'bottom': pyp.Interface(self, self.edges[1])
        }

        # Default placement
        self.set_pivot(open_shape[-1].end)
        self.translate_to([
            - body['sholder_w'] / 2 - opening_depth * 1.5, 
            body['height'] - body['head_l'] + 7, 
            0])  #  - low_depth / 2


class Sleeve(pyp.Component):

    def __init__(self, tag, body, design, depth_diff) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        design = design['sleeve']
        inclanation = design['inclanation']['v']

        pose_angle = np.deg2rad(body['arm_pose_angle'])
        shoulder_angle = np.deg2rad(body['shoulder_incl'])
        standing = design['standing_shoulder']['v']

        base_angle = pose_angle if standing else shoulder_angle
        
        # Pre-compute opening shape
        # TODO was it better when incl_smoothing was inside?
        incl_smoothing = inclanation * design['smoothing_coeff']['v']   # smoothing distance for ArmholeSmooth
        armhole = globals()[design['armhole_shape']['v']]
        proj_shape_front, open_shape_front = armhole(
            inclanation  + depth_diff, design['connecting_depth']['v'], angle=base_angle, 
            incl_smoothing=incl_smoothing, w_coeff=design['smoothing_coeff']['v'])

        proj_shape_back, open_shape_back = armhole(
            inclanation, design['connecting_depth']['v'], angle=base_angle, 
            incl_smoothing=incl_smoothing, w_coeff=design['smoothing_coeff']['v'])

        print(
            'Width!! ', 
            self._arm_fabric_width(open_shape_front),
            self._arm_fabric_width(open_shape_back))

        w_front, w_back = self._arm_fabric_width(open_shape_front), self._arm_fabric_width(open_shape_back)
        fr_frac = w_front / (w_front + w_back)

        # sleeves
        self.f_sleeve = SleevePanel(
            f'{tag}_f', body, design, 
            proj_shape_front, open_shape_front,
            inclanation + depth_diff, 
            design['end_width']['v'] * fr_frac).translate_by([0, 0, 30])
        self.b_sleeve = SleevePanel(
            f'{tag}_b', body, design, 
            proj_shape_back, open_shape_back,
            inclanation, 
            design['end_width']['v'] * (1 - fr_frac)).translate_by([0, 0, -25])

        # DEBUG
        print(
            'Top Len Diff ', 
            self.f_sleeve.interfaces['top'].edges.length(), 
            self.b_sleeve.interfaces['top'].edges.length())

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

    def _arm_fabric_width(self, open_shape):
        """Get the width of a sleeve fabic piece given 
            the open shape of the armhole
        """
        s = open_shape.shortcut()
        s = s[1] - s[0]

        l = open_shape[0]  # edge perpendicular to the main fabic body
        l = np.asarray(l.end) - np.asarray(l.start)
        l = l / np.linalg.norm(l)

        return np.dot(s, l)  


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

    return edges, sleeve_edges


def ArmholeSmooth(incl, width, angle, incl_smoothing, w_coeff=0.2):
    """Piece-wise smooth armhole shape"""
    
    incl_diff = incl - incl_smoothing
    edges = pyp.esf.from_verts([0, 0], [incl_diff, w_coeff * width],  [incl, width])

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyp.esf.from_verts(
        [incl_diff + l*sina, w_coeff * width - l*cosa], 
        [incl_diff, w_coeff * width],  [incl, width])

    return edges, sleeve_edges