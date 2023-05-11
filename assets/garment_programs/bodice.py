from copy import copy
import numpy as np

# Custom
import pypattern as pyp

# other assets
from . import sleeves
from . import collars
from . import tee

class BodiceFrontHalf(pyp.Panel):
    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        design = design['bodice']
        # account for ease in basic measurements
        m_bust = body['bust'] + design['ease']['v']
        m_waist = body['waist'] + design['ease']['v']

        # sizes   
        max_len = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2

        front_frac = (body['bust'] - body['back_width']) / 2 / body['bust'] 

        self.width = front_frac * m_bust
        waist = front_frac * m_waist
        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        bottom_d_width = (self.width - waist) * 2 / 3

        # side length is adjusted due to shoulder inclanation
        # for the correct sleeve fitting
        fb_diff = (front_frac - (0.5 - front_frac)) * body['bust']
        side_len = body['waist_line'] - sh_tan * fb_diff

        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-m_waist / 4 - bottom_d_width, 0],   # Extra point for correct connections at the bottom
            [-self.width, 0], 
            [-self.width, max_len], 
            [0, max_len + shoulder_incl], 
            loop=True
        )

        front_bottom_part_edge = self.edges[1]

        # Side dart
        bust_line = body['waist_line'] - body['bust_line']
        side_d_depth = 0.8 * (self.width - bust_point)    # NOTE: calculated value 
        side_d_width = max_len - side_len
        s_edge, s_dart_edges, side_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(side_d_width, side_d_depth), 
            self.edges[2], 
            offset=bust_line + side_d_width / 2, right=True)
        self.edges.substitute(2, s_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, s_dart_edges[0]), pyp.Interface(self, s_dart_edges[1])))

        # Bottom dart
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, 1. * bust_line), 
            self.edges[0], 
            offset=bust_point, right=True)
        self.edges.substitute(0, b_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

        # Take some fabric from side in the bottom 
        front_bottom_part_edge.end[0] = - (waist + bottom_d_width)

        # Interfaces
        self.interfaces = {
            'outside':  pyp.Interface(self, side_interface),   # side_interface,    # pyp.Interface(self, [side_interface]),  #, self.edges[-3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom_front': pyp.Interface(self, b_interface),
            'bottom_back': pyp.Interface(self, front_bottom_part_edge),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - max_len, 0])


class BodiceBackHalf(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        design = design['bodice']

        # account for ease in basic measurements
        m_bust = body['bust'] + design['ease']['v']
        m_waist = body['waist'] + design['ease']['v']

        # Overall measurements
        length = body['waist_line']
        back_fraction = body['back_width'] / body['bust'] / 2
        
        self.width = back_fraction * m_bust
        waist = back_fraction * m_waist
        waist_width = self.width - (self.width - waist) / 3   # slight inclanation on the side

        shoulder_incl = np.tan(np.deg2rad(body['shoulder_incl'])) * self.width

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-self.width, body['waist_line'] - body['bust_line']],  # from the bottom
            [-self.width, length],   
            [0, length + shoulder_incl],   # Add some fabric for the neck (inclanation of shoulders)
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, [self.edges[1], self.edges[2]]),  #, self.edges[3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        bottom_d_width = (self.width - waist) * 2 / 3
        bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
        bottom_d_position = body['bust_points'] / 2

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = pyp.Interface(self, b_interface)

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))


class BodiceHalf(pyp.Component):
    """Definition of a half of an upper garment with sleeves and collars"""

    def __init__(self, name, body, design, fitted=True) -> None:
        super().__init__(name)

        # Torso
        if fitted:
            self.ftorso = BodiceFrontHalf(f'{name}_ftorso', body, design).translate_by([0, 0, 25])
            self.btorso = BodiceBackHalf(f'{name}_btorso', body, design).translate_by([0, 0, -20])
        else:
            self.ftorso = tee.TorsoFrontHalfPanel(f'{name}_ftorso', body, design).translate_by([0, 0, 25])
            self.btorso = tee.TorsoBackHalfPanel(f'{name}_btorso', body, design).translate_by([0, 0, -20])

        if design['bodice']['strapless']['v']:
            self.make_strapless(design)
        else:
            # Sleeves and collars 
            self.add_sleeves(name, body, design)
            self.add_collars(body, design)

        # Main connectivity
        self.stitching_rules.append((self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']))   # sides
        self.stitching_rules.append((self.ftorso.interfaces['shoulder'], self.btorso.interfaces['shoulder']))  # tops

        self.interfaces = {
            'front_in': self.ftorso.interfaces['inside'],
            'back_in': self.btorso.interfaces['inside'],

            'f_bottom': self.ftorso.interfaces['bottom_front'],
            'b_bottom': pyp.Interface.from_multiple(
                self.btorso.interfaces['bottom'], self.ftorso.interfaces['bottom_back'])
        }

    def add_sleeves(self, name, body, design):

        diff = self.ftorso.width - self.btorso.width
        self.sleeve = sleeves.Sleeve(name, body, design, depth_diff=diff)

        _, f_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_front_shape'].projecting_edges(), 
            self.ftorso.interfaces['shoulder_corner'])
        _, b_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_back_shape'].projecting_edges(), 
            self.btorso.interfaces['shoulder_corner'])

        if design['sleeve']['sleeveless']['v']:  
            # No sleeve component, only the cut remains
            del self.sleeve
        else:
            # Ordering
            bodice_sleeve_int = pyp.Interface.from_multiple(
                f_sleeve_int.reverse(),
                b_sleeve_int.reverse())
            self.stitching_rules.append((
                self.sleeve.interfaces['in'], 
                bodice_sleeve_int
            ))
            self.sleeve.place_by_interface(
                self.sleeve.interfaces['in'], 
                bodice_sleeve_int, 
                gap=7
            )
    
    def add_collars(self, body, design):
        # TODO collars with extra panels!

        # Collar depth is given w.r.t. length.
        # adjust for the shoulder inclination
        width = design['collar']['width']['v']
        tg = np.tan(np.deg2rad(body['shoulder_incl']))
        f_depth_adj = tg * (self.ftorso.width - width / 2)
        b_depth_adj = tg * (self.btorso.width - width / 2)

        # Front
        collar_type = getattr(collars, design['collar']['f_collar']['v'])
        f_collar = collar_type(
            design['collar']['fc_depth']['v'] + f_depth_adj, 
            width, 
            angle=design['collar']['fc_angle']['v'])
        pyp.ops.cut_corner(f_collar, self.ftorso.interfaces['collar_corner'])

        # Back
        collar_type = getattr(collars, design['collar']['b_collar']['v'])
        b_collar = collar_type(
            design['collar']['bc_depth']['v'] + b_depth_adj, 
            width, 
            angle=design['collar']['bc_angle']['v'])
        pyp.ops.cut_corner(b_collar, self.btorso.interfaces['collar_corner'])

    def make_strapless(self, design):

        out_depth = design['sleeve']['connecting_width']['v']
        f_in_depth = design['collar']['fc_depth']['v']
        b_in_depth = design['collar']['bc_depth']['v']
        self._adjust_top_level(self.ftorso, out_depth, f_in_depth)
        self._adjust_top_level(self.btorso, out_depth, b_in_depth)

    def _adjust_top_level(self, panel, out_level, in_level):
        """NOTE: Assumes the top of the panel is a single edge
            and adjustment can be made vertically
        """

        panel_top = panel.interfaces['shoulder'].edges[0]
        min_y = min(panel_top.start[1], panel_top.end[1])

        # Order vertices
        ins, out = panel_top.start, panel_top.end
        if panel_top.start[1] < panel_top.end[1]:
            ins, out = out, ins
  
        ins[1] = min_y - in_level
        out[1] = min_y - out_level


class Shirt(pyp.Component):
    """Panel for the front of upper garments with darts to properly fit it to the shape"""

    def __init__(self, body, design, fitted=False) -> None:
        name_with_params = f"{self.__class__.__name__}"
        super().__init__(name_with_params)

        self.right = BodiceHalf(f'right', body, design, fitted=fitted)
        if design['left']['enable_asym']['v']:
            self.left = BodiceHalf(f'left', body, design['left'], fitted=fitted).mirror()

        self.stitching_rules.append((self.right.interfaces['front_in'], self.left.interfaces['front_in']))
        self.stitching_rules.append((self.right.interfaces['back_in'], self.left.interfaces['back_in']))

        # Adjust interface ordering for correct connectivity
        self.left.interfaces['b_bottom'].reverse()
        if fitted: 
            self.right.interfaces['f_bottom'].reorder([0, 1], [1, 0])

        self.interfaces = {   # Bottom connection
            'bottom': pyp.Interface.from_multiple(
                self.right.interfaces['f_bottom'],
                self.left.interfaces['f_bottom'],
                self.left.interfaces['b_bottom'],
                self.right.interfaces['b_bottom'],)
        }

class FittedShirt(Shirt):
    """Creates fitted shirt
    
        NOTE: Separate class is used for selection convenience.
        Even though most of the processing is the same 
        (hence implemented with the same components except for panels), 
        design parametrization differs significantly. 
        With that, we decided to separate the top level names
    """
    def __init__(self, body, design) -> None:
        super().__init__(body, design, fitted=True)
