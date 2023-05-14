# Custom
import pypattern as pyp
from scipy.spatial.transform import Rotation as R
import numpy as np


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

        # Depends on leg length
        length = body['hips_line'] + design['length']['v'] * body['leg_length']

        waist_rad = waist / (suns * 2 * np.pi)
        arc = suns * 2 * np.pi

        # panels
        self.front = CircleArcPanel(
            f'front_{tag}' if tag else 'front', 
            waist_rad, length, arc / 2).translate_by([0, body['waist_level'], 15])

        self.back = CircleArcPanel(
            f'back_{tag}'  if tag else 'back', 
            waist_rad, length, arc / 2).translate_by([0, body['waist_level'], -15])

        # Add a cut
        if design['cut']['add']['v']:
            self.add_cut(
                self.front if design['cut']['place']['v'] > 0 else self.back, 
                design, length)

        # Stitches
        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Interfaces
        # TODO Update after cut
        self.interfaces = {
            'top': pyp.Interface.from_multiple(self.front.interfaces['top'], self.back.interfaces['top']),
            'bottom': pyp.Interface.from_multiple(self.front.interfaces['bottom'], self.back.interfaces['bottom'])
        }
        
    def add_cut(self, panel, design, sk_length):
        """Add a cut to the skirt"""
        width, depth = design['cut']['width']['v'] * sk_length, design['cut']['depth']['v'] * sk_length

        target_edge = panel.interfaces['bottom'].edges[0]
        t_len = target_edge.length()
        offset = abs(design['cut']['place']['v'] * t_len)

        # Respect the placement boundaries
        offset = max(offset, width / 2)
        offset = min(offset, t_len - width / 2)

        # NOTE: heuristic is specific for the panels that we use
        right = target_edge.start[0] > target_edge.end[0]

        # Make a cut
        cut_shape = pyp.esf.dart_shape(width, depth)
        new_edges, _, interf_edges = pyp.ops.cut_into_edge(
            cut_shape, target_edge, 
            offset=offset, 
            right=right
        )

        panel.edges.substitute(target_edge, new_edges)
        panel.interfaces['bottom'].edges.substitute(target_edge, interf_edges)