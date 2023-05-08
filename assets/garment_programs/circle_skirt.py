# Custom
import pypattern as pyp
from scipy.spatial.transform import Rotation as R
import numpy as np

# other assets
from .bands import WB

# TODO Edge factory?? Then scale, location specification is on the panel
class CircleArcPanel(pyp.Panel):
    """One panel circle skirt"""

    def __init__(self, name, top_rad, length, angle) -> None:
        super().__init__(name)

        halfarc = angle / 2

        dist_w = 2 * top_rad * np.sin(halfarc)
        dist_out = 2 * (top_rad + length) * np.sin(halfarc)

        vert_len = length * np.cos(halfarc)

        # top
        self.edges.append(pyp.CircleEdge.from_points_radius(
            [-dist_w/2, 0], [dist_w/2, 0], 
            radius=top_rad, large_arc=halfarc > np.pi / 2))

        self.edges.append(pyp.Edge(self.edges[-1].end, [dist_out / 2, -vert_len]))
        
        # Bottom
        self.edges.append(pyp.CircleEdge.from_points_radius(
            self.edges[-1].end, [- dist_out / 2, -vert_len], 
            radius=top_rad + length,
            large_arc=halfarc > np.pi / 2, right=False))

        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            'top': pyp.Interface(self, self.edges[0]).reverse(True),
            'bottom': pyp.Interface(self, self.edges[2]),
            'right': pyp.Interface(self, self.edges[1]),
            'left': pyp.Interface(self, self.edges[3])
        }

class SkirtCircle(pyp.Component):
    """Simple circle skirt"""
    def __init__(self, body, design, tag='') -> None:
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')

        design = design['flare-skirt']

        waist = body['waist']
        suns = design['suns']['v']

        # TODO Should be part of smart parameters evaluation
        length = body['hips_line'] + design['length']['v'] * (body['waist_level'] - body['hips_line'])

        waist_rad = waist / (suns * 2 * np.pi)
        arc = suns * 2 * np.pi

        # panels
        self.front = CircleArcPanel(
            f'front_{tag}' if tag else 'front', 
            waist_rad, length, arc / 2).translate_by([0, body['waist_level'], 15])
        self.front.rotate_to(R.from_euler('XYZ', [-40, 0, 0], degrees=True))

        self.back = CircleArcPanel(
            f'back_{tag}'  if tag else 'back', 
            waist_rad, length, arc / 2).translate_by([0, body['waist_level'], -15])
        self.back.rotate_to(R.from_euler('XYZ', [40, 0, 0], degrees=True))

        # Stitches
        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Interfaces
        self.interfaces = {
            'top': pyp.Interface.from_multiple(self.front.interfaces['top'], self.back.interfaces['top']),
            'bottom': pyp.Interface.from_multiple(self.front.interfaces['bottom'], self.back.interfaces['bottom'])
        }
        