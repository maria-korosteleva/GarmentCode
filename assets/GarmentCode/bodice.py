from copy import copy

# Custom
import pypattern as pyp

# other assets
from .sleeves import *


class BodiceFrontHalf(pyp.Panel):
    """Half of the front of the Fitted bodice pattern"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        shoulder_width = body['sholder_w'] / 2  # TODO Also use?
        waist = body['waist'] / 4
        bust_size = body['bust'] / 4
        underbust_size = body['underbust'] / 4
        side_length = body['waist_line']
        max_length = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2

        bottom_width = bust_size - 0.5 * (bust_size - waist)  # with unstitches dart
        bottom_d_width = design['bottom_d_width']['v']
        bottom_d_depth = design['bottom_d_depth']['v']
        bottom_d_position = bust_point
    
        collar_depth = design['c_depth']['v']
        ease = design['ease']['v'] / 4

        width = bust_size + ease
        sholder_top_l = width - body['neck_w']/ 2 
        side_dart_from_top = body['bust_line']
        side_d_depth = bust_size - bust_point - ease   # NOTE: calculated value

        # Bottom dart
        # TODO DO as cutout for nice line at the bottom
        b_edge, _, b_interface, b_dart_stitch = pyp.esf.side_with_dart_by_len(
            [0, 0], [-bottom_width, 0], 
            target_len=waist, depth=bottom_d_depth, dart_position=bottom_d_position, 
            right=True, panel=self)

        self.edges.append(b_edge)

        side_edges, _, side_interface, side_dart_stitch = pyp.esf.side_with_dart_by_len(
            self.edges[-1].end, [-width, max_length], 
            target_len=side_length, depth=side_d_depth, dart_position=(side_length - side_dart_from_top),   # NOTE Assuming l_section is shorter
            right=True, 
            panel=self)

        self.edges.append(side_edges)

        # Collar
        top_and_collar = pyp.esf.from_verts(
            self.edges[-1].end, 
            [-width + sholder_top_l, max_length], 
            [0, max_length - collar_depth])
        self.edges.append(top_and_collar)
        self.edges.close_loop()

        # Stitch the darts
        self.stitching_rules.append(side_dart_stitch)
        self.stitching_rules.append(b_dart_stitch)

        # default placement
        self.translate_by([0, 30 - max_length, 0])

        # Out interfaces
        # TODO Corner by reference self.sleeve_corner = [side_edges[-1], top_and_collar[0]]
        self.interfaces = {
            'outside': side_interface,
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-3]),
            'bottom': b_interface
        }

class BodiceBackHalf(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Make an actual fitted back

        neck_w = body['neck_w']
        sholder_w = body['sholder_w']
        
        design = design['bodice']
        length = design['length']['v']
        c_depth = design['c_depth']['v']
        ease = design['ease']['v']

        width = sholder_w + ease
        shoulder_top_l = (width - neck_w) / 2 
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [0, length], 
            [shoulder_top_l, length], 
            [width / 2, length - c_depth], 
            [width / 2, 0], 
            loop=True)

        # default placement
        self.translate_by([-width / 2, 30 - length, 0])

        self.interfaces = {
            'outside': pyp.Interface(self, self.edges[0]),
            'inside': pyp.Interface(self, self.edges[3]),
            'shoulder': pyp.Interface(self, self.edges[1]),
            'bottom': pyp.Interface(self, self.edges[4]),
        }


# TODO Add design conditions -- e.g. with bottom dart or with ruffles
class FittedShirtHalf(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, name, body_opt, design_opt) -> None:
        # TODO Add params to the base classes?
        super().__init__(name)

        # sleeves
        self.sleeve = SimpleSleeve(f'{name}_sl', body_opt, design_opt)

        # Torso
        self.ftorso = BodiceFrontHalf(f'{name}_ftorso', body_opt, design_opt).translate_by([0, 0, 20])

        # TODO fitted back as well
        self.btorso = BodiceBackHalf(f'{name}_btorso', body_opt, design_opt).translate_by([0, 0, -20])

        # Order of edges updated after (autonorm)..
        # TODO Simplify the choice of the edges to project from/to (regardless of autonorm)
        _, fr_sleeve_int = pyp.ops.cut_corner(self.sleeve.interfaces[0].projecting_edges(), self.ftorso, 2, 3)
        _, br_sleeve_int = pyp.ops.cut_corner(self.sleeve.interfaces[1].projecting_edges(), self.btorso, 0, 1)

        self.stitching_rules = pyp.Stitches(
            # sides
            (self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']),

            # tops
            (self.ftorso.interfaces['shoulder'], self.btorso.interfaces['shoulder']),

            # Sleeves are connected by new interfaces
            (self.sleeve.interfaces[0], fr_sleeve_int),
            (self.sleeve.interfaces[1], br_sleeve_int),
        )

        self.interfaces = [
            self.ftorso.interfaces['inside'],  # TODO correct ids??
            self.btorso.interfaces['inside'],

            # bottom
            self.ftorso.interfaces['bottom'],
            self.btorso.interfaces['bottom'],
        ]


class FittedShirt(pyp.Component):
    """Panel for the front of upper garments with darts to properly fit it to the shape"""

    def __init__(self, body, design) -> None:
        name_with_params = f"{self.__class__.__name__}_l{design['bodice']['length']['v']}_s{body['sholder_w']}_b{body['bust_line']}"
        super().__init__(name_with_params)

        # TODO resolving names..
        self.right = FittedShirtHalf(f'right', body, design)
        self.left = FittedShirtHalf(f'left', body, design).mirror()

        self.stitching_rules.append((self.right.interfaces[0], self.left.interfaces[0]))
        self.stitching_rules.append((self.right.interfaces[1], self.left.interfaces[1]))

        self.interfaces = [   # Bottom connection
            self.right.interfaces[2],
            self.right.interfaces[3],
            self.left.interfaces[2],
            self.left.interfaces[3],
        ]
