from copy import copy

# Custom
import pypattern as pyp

# other assets
from . import sleeves


class BodiceFrontHalf(pyp.Panel):
    """Half of the front of the Fitted bodice pattern"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        ease = design['ease']['v'] / 4

        shoulder_width = body['sholder_w'] / 2  # TODO Also use?
        
        bust_size = body['bust'] / 4
        underbust_size = body['underbust'] / 4

        side_length = body['waist_line']
        max_length = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2
        front_width = (body['bust'] - body['back_width'] - body['bust_points']) / 4 + bust_point + ease
        front_fraction = front_width / (body['bust'] + ease * 4)
        waist = (body['waist'] + ease*4) * front_fraction

        bottom_d_width = (body['bust'] - body['waist']) / 6

        # DRAFT bottom_width = bust_size - 0.5 * (bust_size - waist)  # with unstitches dart
        bottom_width = waist + bottom_d_width
        bottom_d_depth = design['bottom_d_depth']['v']
        bottom_d_position = bust_point
    
        collar_depth = design['c_depth']['v']
        
        sholder_top_l = front_width - body['neck_w']/ 2 
        side_dart_from_top = body['bust_line']
        side_d_depth = bust_size - bust_point - ease   # NOTE: calculated value

        # Bottom dart as cutout -- for straight line
        b_edge = pyp.LogicalEdge([0, 0], [-bottom_width, 0])
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), b_edge, 
            offset=bottom_d_position, right=True)
        self.edges.append(b_edge)

        # side dart
        side_edges, _, side_interface, side_dart_stitch = pyp.esf.side_with_dart_by_len(
            self.edges[-1].end, [-front_width, max_length], 
            target_len=side_length, depth=side_d_depth, dart_position=(side_length - side_dart_from_top),   # NOTE Assuming l_section is shorter
            right=True, 
            panel=self)

        self.edges.append(side_edges)

        # Collar
        # TODO Collars are to be defined sparately
        top_and_collar = pyp.esf.from_verts(
            self.edges[-1].end, 
            [-front_width + sholder_top_l, max_length], 
            [0, max_length - collar_depth])
        self.edges.append(top_and_collar)
        self.edges.close_loop()

        # Reference to the corner for sleeve projection
        self.shoulder_corner = pyp.EdgeSequence(side_edges[-1], top_and_collar[0])

        # Stitch the darts
        self.stitching_rules.append(side_dart_stitch)
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

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
        length = body['waist_line']
        c_depth = design['c_depth']['v']   # TODO collar is a separate thing
        ease = design['ease']['v'] / 4

        # bottom dart
        bottom_d_width = (body['bust'] - body['waist']) / 6
        bottom_d_depth = design['bottom_d_depth']['v']   # TODO different depth?
        bottom_d_position = body['bust_points'] / 2

        # Overall measurements
        width = body['back_width'] / 2 + (body['bust'] - body['back_width'] - body['bust_points']) / 4 + ease

        back_fraction = width / (body['bust'] + ease * 4)
        waist = (body['waist'] + ease*4) * back_fraction
        waist_width = waist + bottom_d_width
        shoulder_top_l = width - neck_w / 2 

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-width, length], 
            [-width + shoulder_top_l, length], 
            [0, length - c_depth], 
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, self.edges[1]),
            'inside': pyp.Interface(self, self.edges[4]),
            'shoulder': pyp.Interface(self, self.edges[2]),
        }
        # For projection of the sleeves
        self.shoulder_corner = pyp.EdgeSequence(self.edges[1], self.edges[2])

        # Bottom dart as cutout -- for straight line
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = b_interface

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))


# TODO Add design conditions -- e.g. with bottom dart or with ruffles
class FittedShirtHalf(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, name, body_opt, design_opt, sleeve=True) -> None:
        # TODO Add params to the base classes?
        super().__init__(name)

        # Torso
        self.ftorso = BodiceFrontHalf(f'{name}_ftorso', body_opt, design_opt).translate_by([0, 0, 20])
        # TODO fitted back as well
        self.btorso = BodiceBackHalf(f'{name}_btorso', body_opt, design_opt).translate_by([0, 0, -20])

        sleeve_type = getattr(sleeves, design_opt['bodice']['sleeves']['v'])
        self.sleeve = sleeve_type(f'{name}_sl', body_opt, design_opt)
        if isinstance(self.sleeve, pyp.Component):
            # Order of edges updated after (autonorm)..
            _, fr_sleeve_int = pyp.ops.cut_corner(self.sleeve.interfaces[0].projecting_edges(), self.ftorso, self.ftorso.shoulder_corner)
            _, br_sleeve_int = pyp.ops.cut_corner(self.sleeve.interfaces[1].projecting_edges(), self.btorso, self.btorso.shoulder_corner)

            # Sleeves are connected by new interfaces
            self.stitching_rules.append((self.sleeve.interfaces[0], fr_sleeve_int))
            self.stitching_rules.append((self.sleeve.interfaces[1], br_sleeve_int))
        else:   # it's just an edge sequence to define sleeve shape
            # Simply do the projection -- no new stitches needed
            _, fr_sleeve_int = pyp.ops.cut_corner(self.sleeve, self.ftorso, self.ftorso.shoulder_corner)
            _, br_sleeve_int = pyp.ops.cut_corner(self.sleeve, self.btorso, self.btorso.shoulder_corner)

        self.stitching_rules.append((self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']))   # sides
        self.stitching_rules.append((self.ftorso.interfaces['shoulder'], self.btorso.interfaces['shoulder']))  # tops


        self.interfaces = [
            self.ftorso.interfaces['inside'],  
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
