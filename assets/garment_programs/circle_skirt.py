import numpy as np
import pypattern as pyp

from assets.garment_programs.base_classes import StackableSkirtComponent


class CircleArcPanel(pyp.Panel):
    """One panel circle skirt"""

    def __init__(self, name, top_rad, length, angle) -> None:
        super().__init__(name)

        halfarc = angle / 2

        dist_w = 2 * top_rad * np.sin(halfarc)
        dist_out = 2 * (top_rad + length) * np.sin(halfarc)

        vert_len = length * np.cos(halfarc)

        # top
        self.edges.append(pyp.CircleEdgeFactory.from_points_radius(
            [-dist_w/2, 0], [dist_w/2, 0], 
            radius=top_rad, large_arc=halfarc > np.pi / 2))

        self.edges.append(pyp.Edge(
            self.edges[-1].end, [dist_out / 2, -vert_len]))
        
        # Bottom
        self.edges.append(pyp.CircleEdgeFactory.from_points_radius(
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

    def length(self, *args):
        return self.interfaces['right'].edges.length()
    
    @staticmethod
    def from_w_length_suns(name, length, top_width, sun_fraction):
        arc = sun_fraction * 2 * np.pi
        rad = top_width / arc

        return CircleArcPanel(name, rad, length, arc)
    
    @staticmethod
    def from_all_length(name, length, top_width, bottom_width):

        diff = bottom_width - top_width
        arc = diff / length
        rad = top_width / arc

        return CircleArcPanel(name, rad, length, arc)
    
    @staticmethod
    def from_length_rad(name, length, top_width, rad):

        arc = top_width / rad

        return CircleArcPanel(name, rad, length, arc)

class AsymHalfCirclePanel(pyp.Panel):
    """Panel for a asymmetrci circle skirt"""

    def __init__(self, name, top_rad, length_f, length_s) -> None:
        """ Half a shifted arc section
        """
        super().__init__(name)

        dist_w = 2 * top_rad 
        dist_out = 2 * (top_rad + length_s)

        # DRAFT vert_len = length * np.cos(halfarc)

        # top
        self.edges.append(pyp.CircleEdgeFactory.from_points_radius(
            [-dist_w/2, 0], [dist_w/2, 0], 
            radius=top_rad, large_arc=False))

        self.edges.append(pyp.Edge(
            self.edges[-1].end, [dist_out / 2, 0]))
        
        # Bottom
        self.edges.append(
            pyp.CircleEdgeFactory.from_three_points(
                self.edges[-1].end, [- dist_out / 2, 0], 
                point_on_arc=[0, -(top_rad + length_f)]
            )
        )

        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            'top': pyp.Interface(self, self.edges[0]).reverse(True),
            'bottom': pyp.Interface(self, self.edges[2]),
            'left': pyp.Interface(self, self.edges[1]),
            'right': pyp.Interface(self, self.edges[3])
        }
    
    def length(self, *args):
        return self.interfaces['right'].edges.length()

class SkirtCircle(StackableSkirtComponent):
    """Simple circle skirt"""
    def __init__(self, body, design, tag='', length=None, rise=None, slit=True, asymm=False, min_len=5, **kwargs) -> None:
        super().__init__(body, design, tag)

        design = design['flare-skirt']
        suns = design['suns']['v']
        self.rise = design['rise']['v'] if rise is None else rise
        waist, hips_depth, _ = self.eval_rise(self.rise)

        if length is None:  # take from design parameters
            length = hips_depth + design['length']['v'] * body['_leg_length']

        # NOTE: with some combinations of rise and length parameters length may become too small/negative
        # Hence putting a min positive value here
        length = max(length, min_len)

        # panels
        if not asymm:  # Typical symmetric skirt
            self.front = CircleArcPanel.from_w_length_suns(
                f'skirt_front_{tag}' if tag else 'skirt_front', 
                length, waist / 2, suns / 2).translate_by([0, body['_waist_level'], 15])

            self.back = CircleArcPanel.from_w_length_suns(
                f'skirt_back_{tag}'  if tag else 'skirt_back', 
                length, waist / 2, suns / 2).translate_by([0, body['_waist_level'], -15])
        else:
            # NOTE: Asymmetic front/back is only defined on full skirt (1 sun)
            w_rad = waist / 2 / np.pi
            f_length = design['asymm']['front_length']['v'] * length
            tot_len = w_rad * 2 + length + f_length 
            del_r = tot_len / 2 - f_length - w_rad
            s_length = np.sqrt((tot_len / 2)**2 - del_r**2) - w_rad

            self.front = AsymHalfCirclePanel(
                f'skirt_front_{tag}' if tag else 'skirt_front', 
                w_rad, f_length, s_length).translate_by([0, body['_waist_level'], 15])

            self.back = AsymHalfCirclePanel(
                f'skirt_back_{tag}'  if tag else 'skirt_back', 
                w_rad, length, s_length).translate_by([0, body['_waist_level'], -15])

        # Add a cut
        if design['cut']['add']['v'] and slit:
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
            'bottom_f': self.front.interfaces['bottom'],
            'bottom_b': self.back.interfaces['bottom'],
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
        cut_shape = pyp.EdgeSeqFactory.dart_shape(width, depth=depth)

        new_edges, _, interf_edges = pyp.ops.cut_into_edge(
            cut_shape, target_edge, 
            offset=offset, 
            right=right
        )

        panel.edges.substitute(target_edge, new_edges)
        panel.interfaces['bottom'].substitute(
            target_edge, interf_edges,
            [panel for _ in range(len(interf_edges))])
        
    def length(self, *args):
        return self.front.length()


class AsymmSkirtCircle(SkirtCircle):
    """Front/back asymmetric skirt"""
    def __init__(self, body, design, tag='', length=None, rise=None, slit=True, **kwargs):
        super().__init__(body, design, tag, length, rise, slit, asymm=True)