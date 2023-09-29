from copy import copy, deepcopy
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

        # account for ease in basic measurements
        m_bust = body['bust']
        m_waist = body['waist']

        # sizes   
        max_len = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2

        front_frac = (body['bust'] - body['back_width']) / 2 / body['bust'] 

        self.width = front_frac * m_bust
        waist = (m_waist - body['waist_back_width']) / 2  # DRAFT front_frac * m_waist
        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        bottom_d_width = (self.width - waist) * 2 / 3   # TODO probably need a correction here!

        # side length is adjusted due to shoulder inclination
        # for the correct sleeve fitting
        fb_diff = (front_frac - (0.5 - front_frac)) * body['bust']
        side_len = body['waist_line'] - sh_tan * fb_diff

        self.edges = pyp.esf.from_verts(
            [0, 0], 
            # DRAFT Not needed anymore [-m_waist / 4 - bottom_d_width, 0],   # Extra point for correct connections at the bottom
            [-self.width, 0],  # DRAFT [-self.width, 0], 
            [-self.width, max_len], 
            [0, max_len + shoulder_incl], 
            loop=True
        )

        # DRAFT front_bottom_part_edge = self.edges[1]

        # Side dart
        bust_line = body['waist_line'] - body['bust_line']
        side_d_depth = 0.8 * (self.width - bust_point)    # NOTE: calculated value 
        side_d_width = max_len - side_len
        s_edge, s_dart_edges, side_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(side_d_width, side_d_depth), 
            self.edges[1], 
            offset=bust_line + side_d_width / 2, right=True)
        self.edges.substitute(1, s_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, s_dart_edges[0]), pyp.Interface(self, s_dart_edges[1])))

        # DEBUG
        print('Side edge len ', s_edge.lengths(), bust_line + side_d_width / 2, bust_line)

        # Bottom dart
        # DEBUG
        print('Bottom Dart')

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, 1. * bust_line),   # FIXME is this correct???
            self.edges[0], 
            offset=bust_point + bottom_d_width / 2, right=True)
        self.edges.substitute(0, b_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))
        
        # DEBUG
        print('Bottom edge len ', b_edge.lengths(), bust_point + bottom_d_width / 2, bust_point)

        # Take some fabric from side in the bottom (!: after side dart insertion)
        # DRAFT front_bottom_part_edge.end[0] 
        b_edge[-1].end[0] = - (waist + bottom_d_width) 

        # Interfaces
        self.interfaces = {
            'outside':  pyp.Interface(self, side_interface),   # side_interface,    # pyp.Interface(self, [side_interface]),  #, self.edges[-3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom_front': pyp.Interface(self, b_interface),
            # DRAFT 'bottom_back': pyp.Interface(self, front_bottom_part_edge),
            
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

        # account for ease in basic measurements
        m_bust = body['bust']
        m_waist = body['waist']

        # Overall measurements
        length = body['waist_line']
        back_fraction = body['back_width'] / body['bust'] / 2
        
        self.width = back_fraction * m_bust
        waist = body['waist_back_width'] / 2   # back_fraction * m_waist
        # slight inclination on the side
        waist_width = self.width - (self.width - waist) / 3 if waist < self.width else waist   

        shoulder_incl = np.tan(np.deg2rad(body['shoulder_incl'])) * self.width

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-self.width, body['waist_line'] - body['bust_line']],  # from the bottom
            [-self.width, length],   
            [0, length + shoulder_incl],   # Add some fabric for the neck (inclination of shoulders)
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, [self.edges[1], self.edges[2]]),  #, self.edges[3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, self.edges[0]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        if waist < self.width:
            bottom_d_width = (self.width - waist) * 2 / 3
            bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
            bottom_d_position = body['bum_points'] / 2

            b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
                pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
                offset=bottom_d_position + bottom_d_width / 2, right=True)

            self.edges.substitute(0, b_edge)
            self.interfaces['bottom'] = pyp.Interface(self, b_interface)

            # DEBUG
            print('Bottom edge len ', b_edge.lengths(), bottom_d_position + bottom_d_width / 2, bottom_d_position)

            # Stitch the dart
            self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length, 0])
        

class BodiceHalf(pyp.Component):
    """Definition of a half of an upper garment with sleeves and collars"""

    def __init__(self, name, body, design, fitted=True) -> None:
        super().__init__(name)

        design = deepcopy(design)   # Recalculate freely!

        # Torso
        if fitted:
            # DEBUG
            print('Front')
            self.ftorso = BodiceFrontHalf(f'{name}_ftorso', body, design).translate_by([0, 0, 25])

            # DEBUG
            print('Back')
            self.btorso = BodiceBackHalf(f'{name}_btorso', body, design).translate_by([0, 0, -20])
        else:
            self.ftorso = tee.TorsoFrontHalfPanel(f'{name}_ftorso', body, design).translate_by([0, 0, 25])
            self.btorso = tee.TorsoBackHalfPanel(f'{name}_btorso', body, design).translate_by([0, 0, -20])

        # Interfaces
        self.interfaces.update({
            'f_bottom': self.ftorso.interfaces['bottom_front'],
            # DRAFT -- not needed! 'b_bottom': pyp.Interface.from_multiple(
            #    self.btorso.interfaces['bottom'], self.ftorso.interfaces['bottom_back']),
            'b_bottom': self.btorso.interfaces['bottom'],
            'front_in': self.ftorso.interfaces['inside'],
            'back_in': self.btorso.interfaces['inside']
        })

        # Sleeves/collar cuts
        self.eval_dep_params(body, design)
        if design['shirt']['strapless']['v']:
            self.make_strapless(design)
        else:
            # Sleeves and collars 
            self.add_sleeves(name, body, design)
            self.add_collars(name, body, design)
            self.stitching_rules.append((
                self.ftorso.interfaces['shoulder'], 
                self.btorso.interfaces['shoulder']
            ))  # tops

        # Main connectivity

        # DEBUG
        print(f'Side Stitch: front {self.ftorso.interfaces["outside"].edges.length()},'
              f' back {self.btorso.interfaces["outside"].edges.length()}')

        self.stitching_rules.append((
            self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']))   # sides


    def eval_dep_params(self, body, design):

        # Sleeves
        # NOTE assuming the vertical side is the first argument
        max_cwidth = self.ftorso.interfaces['shoulder_corner'].edges[0].length() - 1  # cm
        min_cwidth = body['armscye_depth']
        v = design['sleeve']['connecting_width']['v']
        design['sleeve']['connecting_width']['v'] = min_cwidth + v * (max_cwidth - min_cwidth)

        # Collars
        # NOTE: Assuming the first is the top edge
        # Width
        max_edge = self.ftorso.interfaces['collar_corner'].edges[0]
        # NOTE: Back panel is more narrow, so using it
        max_w = 2 * (self.btorso.width - design['sleeve']['inclination']['v'] - 1)
        min_w = body['neck_w']

        if design['collar']['width']['v'] >= 0:
            design['collar']['width']['v'] = width = pyp.utils.lin_interpolation(min_w, max_w, design['collar']['width']['v'])
        else:
            design['collar']['width']['v'] = width = pyp.utils.lin_interpolation(0, min_w, 1 + design['collar']['width']['v'])

        # Depth
        # Collar depth is given w.r.t. length.
        # adjust for the shoulder inclination
        tg = np.tan(np.deg2rad(body['shoulder_incl']))
        f_depth_adj = tg * (self.ftorso.width - width / 2)
        b_depth_adj = tg * (self.btorso.width - width / 2)

        max_f_len = self.ftorso.interfaces['collar_corner'].edges[1].length() - tg * self.ftorso.width - 1  # cm
        max_b_len = self.btorso.interfaces['collar_corner'].edges[1].length() - tg * self.btorso.width - 1  # cm

        
        design['collar']['f_strapless_depth'] = {}
        design['collar']['f_strapless_depth']['v'] = design['collar']['fc_depth']['v'] * max_f_len
        design['collar']['fc_depth']['v'] = design['collar']['f_strapless_depth']['v'] + f_depth_adj
        
        design['collar']['b_strapless_depth'] = {}
        design['collar']['b_strapless_depth']['v'] = design['collar']['bc_depth']['v'] * max_b_len
        design['collar']['bc_depth']['v'] = design['collar']['b_strapless_depth']['v'] + b_depth_adj 

    def add_sleeves(self, name, body, design):

        diff = self.ftorso.width - self.btorso.width

        self.sleeve = sleeves.Sleeve(name, body, design, depth_diff=diff)

        _, f_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_front_shape'].projecting_edges(), 
            self.ftorso.interfaces['shoulder_corner'])
        _, b_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_back_shape'].projecting_edges(), 
            self.btorso.interfaces['shoulder_corner'])

        if not design['sleeve']['sleeveless']['v']:  
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
    
    def add_collars(self, name, body, design):
        # Front
        collar_type = getattr(
            collars, 
            str(design['collar']['component']['style']['v']), 
            collars.NoPanelsCollar
            )
        
        self.collar_comp = collar_type(name, body, design)
        
        # Project shape
        _, fc_interface = pyp.ops.cut_corner(
            self.collar_comp.interfaces['front_proj'].edges, 
            self.ftorso.interfaces['collar_corner']
        )
        _, bc_interface = pyp.ops.cut_corner(
            self.collar_comp.interfaces['back_proj'].edges, 
            self.btorso.interfaces['collar_corner']
        )

        # Add stitches/interfaces
        if 'bottom' in self.collar_comp.interfaces:
            self.stitching_rules.append((
                pyp.Interface.from_multiple(fc_interface, bc_interface), 
                self.collar_comp.interfaces['bottom']
            ))

        # Upd front interfaces accordingly
        if 'front' in self.collar_comp.interfaces:
            self.interfaces['front_collar'] = self.collar_comp.interfaces['front']
            self.interfaces['front_in'] = pyp.Interface.from_multiple(
                self.ftorso.interfaces['inside'], self.interfaces['front_collar']
            )
        if 'back' in self.collar_comp.interfaces:
            self.interfaces['back_collar'] = self.collar_comp.interfaces['back']
            self.interfaces['back_in'] = pyp.Interface.from_multiple(
                self.btorso.interfaces['inside'], self.interfaces['back_collar']
            )

    def make_strapless(self, design):

        out_depth = design['sleeve']['connecting_width']['v']
        f_in_depth = design['collar']['f_strapless_depth']['v']
        b_in_depth = design['collar']['b_strapless_depth']['v']
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

        # NOTE: Support for full collars with partially strapless top
        # requres further development
        # TODOLOW enable this one to work
        if design['left']['enable_asym']['v']:
            if design['shirt']['strapless']['v'] != design['left']['shirt']['strapless']['v']:
                # Force no collars
                design = deepcopy(design)
                design['collar']['component']['style']['v'] = None
                design['left']['collar']['component']['style']['v'] = None

        self.right = BodiceHalf(f'right', body, design, fitted=fitted)
        self.left = BodiceHalf(
            f'left', body, 
            design['left'] if design['left']['enable_asym']['v'] else design, 
            fitted=fitted).mirror()

        self.stitching_rules.append((self.right.interfaces['front_in'], self.left.interfaces['front_in']))
        self.stitching_rules.append((self.right.interfaces['back_in'], self.left.interfaces['back_in']))

        # Adjust interface ordering for correct connectivity
        self.left.interfaces['b_bottom'].reverse()
        if fitted: 
            self.right.interfaces['f_bottom'].reorder([0, 1], [1, 0])

        # DEBUG
        print(f"Bodice front len: {self.right.interfaces['f_bottom'].edges.length() + self.left.interfaces['f_bottom'].edges.length()}")
        print(f"Bodice back len: {self.right.interfaces['b_bottom'].edges.length() + self.left.interfaces['b_bottom'].edges.length()}")

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
