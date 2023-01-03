from copy import copy

# Custom
import pypattern as pyp

# other assets
from .sleeves import *
from .tee import TorsoPanel


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
        b_edge, _, _, b_dart_stitch = pyp.esf.side_with_dart_by_len(
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
        self.interfaces = [
            side_interface,
            pyp.Interface(self, self.edges[-3]),
            pyp.Interface(self, self.edges[-1])
        ]


class BodiceFront(pyp.Component):
    """Panel for the front of upper garments with darts to properly fit it to the shape"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        self.right = BodiceFrontHalf(f'{name}_right', body, design)
        self.left = BodiceFrontHalf(f'{name}_left', body, design).mirror()

        self.stitching_rules.append((self.right.interfaces[-1], self.left.interfaces[-1]))

        self.interfaces = [
            self.right.interfaces[0],
            self.right.interfaces[1],
            self.left.interfaces[1],
            self.left.interfaces[0],
        ]

# TODO Add design conditions -- e.g. with bottom dart or with ruffles
class FittedTShirt(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, body_opt, design_opt) -> None:
        # TODO Add params to the base classes?
        name_with_params = f"{self.__class__.__name__}_l{design_opt['bodice']['length']['v']}_s{body_opt['sholder_w']}_b{body_opt['bust_line']}"
        super().__init__(name_with_params)

        # sleeves
        self.r_sleeve = SimpleSleeve('r', body_opt, design_opt)
        self.l_sleeve = SimpleSleeve('l', body_opt, design_opt).mirror()

        # TODO Make it half from the start

        # Torso
        self.ftorso = BodiceFront('ftorso', body_opt, design_opt).translate_by([0, 0, 20])

        # TODO fitted back as well
        self.btorso = TorsoPanel('btorso', body_opt, design_opt).translate_by([0, 0, -20])

        # Order of edges updated after (autonorm)..
        # TODO Simplify the choice of the edges to project from/to (regardless of autonorm)
        _, fr_sleeve_int = pyp.ops.cut_corner(self.r_sleeve.interfaces[0].projecting_edges(), self.ftorso.right, 2, 3)
        _, fl_sleeve_int = pyp.ops.cut_corner(self.l_sleeve.interfaces[0].projecting_edges(), self.ftorso.left, 4 + 3, 5 + 3)
        _, br_sleeve_int = pyp.ops.cut_corner(self.r_sleeve.interfaces[1].projecting_edges(), self.btorso, 0, 1)
        _, bl_sleeve_int = pyp.ops.cut_corner(self.l_sleeve.interfaces[1].projecting_edges(), self.btorso, 5, 6)

        self.stitching_rules = pyp.Stitches(
            # sides
            (self.ftorso.interfaces[0], self.btorso.interfaces[0]),
            (self.ftorso.interfaces[3], self.btorso.interfaces[3]),

            # tops
            (self.ftorso.interfaces[1], self.btorso.interfaces[1]),
            (self.ftorso.interfaces[2], self.btorso.interfaces[2]),

            # Sleeves are connected by new interfaces
            (self.r_sleeve.interfaces[0], fr_sleeve_int),
            (self.l_sleeve.interfaces[0], fl_sleeve_int),
            (self.r_sleeve.interfaces[1], br_sleeve_int),
            (self.l_sleeve.interfaces[1], bl_sleeve_int),

        )

        # DEBUG
        print('After connecting: ')
        print(self.btorso.interfaces[0])
        print(self.btorso.interfaces[3])