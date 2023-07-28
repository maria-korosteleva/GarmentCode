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
            'left': pyp.Interface(self, self.edges[1]),
            'right': pyp.Interface(self, self.edges[3])
        }
    
    @staticmethod
    def from_w_length_suns(name, length, top_width, sun_fraction):
        arc = sun_fraction * 2 * np.pi
        rad = top_width / arc

        return CircleArcPanel(name, rad, length, arc)
    
    def from_all_length(name, length, top_width, bottom_width):

        diff = bottom_width - top_width
        arc = diff / length
        rad = top_width / arc

        return CircleArcPanel(name, rad, length, arc)
    
    def from_length_rad(name, length, top_width, rad):

        arc = top_width / rad

        return CircleArcPanel(name, rad, length, arc)


# DEBUG This is a test garment!
class MinimalALine(pyp.Component):
    """Simple circle skirt"""
    def __init__(self, body, design, tag='') -> None:
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')

        design = design['flare-skirt']

        waist = body['waist']
        hips = body['hips']
        suns = design['suns']['v']

        # Depends on leg length
        length = body['hips_line'] + design['length']['v'] * body['leg_length']

        # panels
        self.front = CircleArcPanel.from_all_length(
            f'front_{tag}' if tag else 'front', 
            length=body['hips_line'], 
            top_width=waist / 2, 
            bottom_width=hips / 2
        ).translate_by([0, body['waist_level'], 15])

        self.back = CircleArcPanel.from_all_length(
            f'back_{tag}'  if tag else 'back', 
            length=body['hips_line'], 
            top_width=waist / 2, 
            bottom_width=hips / 2
        ).translate_by([0, body['waist_level'], -15])

        # DEBUG
        print('Length: ', self.front.interfaces['right'].edges.length(), body['hips_line'])
        print('waist: ', 
              self.front.interfaces['top'].edges.length() + self.back.interfaces['top'].edges.length(), 
              body['waist'])
        print('hips: ', 
              self.front.interfaces['bottom'].edges.length() + self.back.interfaces['bottom'].edges.length(), 
              body['hips'])
        print('Radius: ', 
              self.front.interfaces['top'].edges[0].as_radius_angle(),
              self.front.interfaces['bottom'].edges[0].as_radius_angle(),
              self.back.interfaces['top'].edges[0].as_radius_angle(),
              self.back.interfaces['bottom'].edges[0].as_radius_angle())

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

        # panels
        self.front = CircleArcPanel.from_w_length_suns(
            f'front_{tag}' if tag else 'front', 
            length, waist / 2, suns / 2).translate_by([0, body['waist_level'], 15])

        self.back = CircleArcPanel.from_w_length_suns(
            f'back_{tag}'  if tag else 'back', 
            length, waist / 2, suns / 2).translate_by([0, body['waist_level'], -15])

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
        panel.interfaces['bottom'].substitute(target_edge, interf_edges, [panel for _ in range(len(interf_edges))])