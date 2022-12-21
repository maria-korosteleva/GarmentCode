from copy import copy

# Custom
import pypattern as pyp


class SleevePanel(pyp.Panel):
    """Simple panel for a sleeve with optional ruffles on the sholder connection"""

    def __init__(self, name, body_opt, design_opt) -> None:
        super().__init__(name)

        arm_width = body_opt['arm_width']
        length = design_opt['sleeve']['length']['v']
        ease = design_opt['sleeve']['ease']['v']
        ruffle = design_opt['sleeve']['ruffle']['v']

        width = ruffle * (arm_width + ease) / 2 
        self.edges = pyp.esf.from_verts([0, 0], [0, width], [length, width], [length - 7, 0], loop=True)

        # default placement
        self.translate_by([-length - 20, 15, 0])

        self.interfaces = [
            pyp.Interface(self, self.edges[1]),
            pyp.Interface(self, self.edges[2], ruffle=ruffle),
            pyp.Interface(self, self.edges[3]),
        ]

class SimpleSleeve(pyp.Component):
    """Very simple sleeve"""
    def __init__(self, tag, body_opt, design_opt) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        # sleeves
        self.f_sleeve = SleevePanel(f'{tag}_f_sleeve', body_opt, design_opt).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(f'{tag}_b_sleeve', body_opt, design_opt).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces[0], self.b_sleeve.interfaces[0]),
            (self.f_sleeve.interfaces[2], self.b_sleeve.interfaces[2]),
        )

        self.interfaces = [
            self.f_sleeve.interfaces[1],
            self.b_sleeve.interfaces[1],
        ]

class TorsoPanel(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

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
            [shoulder_top_l + neck_w, length], 
            [width, length], 
            [width, 0], 
            loop=True)

        # default placement
        self.translate_by([-width / 2, 30 - length, 0])

        self.interfaces = [
            pyp.Interface(self, self.edges[0]),
            pyp.Interface(self, self.edges[1]),
            pyp.Interface(self, self.edges[4]),
            pyp.Interface(self, self.edges[5]),
        ]


class BodiceFrontHalf(pyp.Panel):
    """Half of the front of the Fitted bodice pattern"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        design = design['bodice']
        length = design['length']['v']
        d_width = design['d_width']['v']
        d_depth = design['d_depth']['v']
        c_depth = design['c_depth']['v']
        ease = design['ease']['v']

        width = body['sholder_w'] + ease
        sholder_top_l = (width - body['neck_w']) / 2 
        dart_from_top = body['bust_line']
        bottom_width = body['waist'] / 4 + d_width

        b_section = bottom_width / 3

        print(b_section)  # DEBUG

        # Bottom dart
        b_edge, _, _, b_dart_stitch = pyp.esf.side_with_dart_by_len(
            [0, 0], [-bottom_width, 0], 
            target_len=body['waist'] / 4, depth=20, dart_position=b_section, 
            right=True,
            panel=self)

        self.edges.append(b_edge)

        l_section = length / 3
        print(l_section)  # DEBUG

        # TODO dart depends on bust measurements?
        side_edges, _, side_interface, side_dart_stitch = pyp.esf.side_with_dart_by_len(
            self.edges[-1].end, [-width/2, length], 
            target_len=length*0.95, depth=10, dart_position=(length * 0.95 - dart_from_top),   # NOTE Assuming l_section is shorter
            right=True, 
            panel=self)

        self.edges.append(side_edges)

        print(self.edges)  # DEBUG
        
        #self.edges.append(side_edges)

        # Collar
        self.edges.append(pyp.esf.from_verts(
            self.edges[-1].end, 
            [-width/2 + sholder_top_l, length], 
            [0, length - c_depth]))
        self.edges.close_loop()

        # Stitch the darts
        self.stitching_rules.append(side_dart_stitch)
        self.stitching_rules.append(b_dart_stitch)

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Out interfaces
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



# TODO condition T-Shirts to be fitted or not
class TShirt(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, body_opt, design_opt) -> None:
        name_with_params = f"{self.__class__.__name__}_l{design_opt['bodice']['length']['v']}_s{body_opt['sholder_w']}_b{body_opt['bust_line']}"

        super().__init__(name_with_params if design_opt['sleeve']['ruffle']['v'] == 1 else f'{name_with_params}_Ruffle_sl')

        # sleeves
        self.r_sleeve = SimpleSleeve('r', body_opt, design_opt)
        self.l_sleeve = SimpleSleeve('l', body_opt, design_opt).mirror()

        # Torso
        self.ftorso = TorsoPanel('ftorso', body_opt, design_opt).translate_by([0, 0, 20])
        self.btorso = TorsoPanel('btorso', body_opt, design_opt).translate_by([0, 0, -20])

        # Cut the sleeve shapes to connect them nicely
        _, fr_sleeve_int = pyp.ops.cut_corner(self.r_sleeve.interfaces[0].projecting_edges(), self.ftorso, 5, 6)
        _, fl_sleeve_int = pyp.ops.cut_corner(self.l_sleeve.interfaces[0].projecting_edges(), self.ftorso, 1, 2)
        _, br_sleeve_int = pyp.ops.cut_corner(self.r_sleeve.interfaces[1].projecting_edges(), self.btorso, 0, 1)
        _, bl_sleeve_int = pyp.ops.cut_corner(self.l_sleeve.interfaces[1].projecting_edges(), self.btorso, 5, 6)

        # DRAFT tests of cut-outs
        # dart = pyp.esf.from_verts([0,0], [5, 10], [10, 0], loop=False)
        # eid = 1
        # edges, _ = pyp.ops.cut_into_edge(dart, self.ftorso.edges[eid], 0.3, right=False)

        # self.ftorso.edges.substitute(eid, edges)

        # eid = 0
        # edges, _ = pyp.ops.cut_into_edge(dart, self.btorso.edges[eid], 0.3, right=True)
        # self.btorso.edges.substitute(eid, edges)

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

class FittedTShirt(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, body_opt, design_opt) -> None:
        # TODO Add params to the base classes?
        name_with_params = f"{self.__class__.__name__}_l{design_opt['bodice']['length']['v']}_s{body_opt['sholder_w']}_b{body_opt['bust_line']}"
        super().__init__(name_with_params)

        # sleeves
        self.r_sleeve = SimpleSleeve('r', body_opt, design_opt)
        self.l_sleeve = SimpleSleeve('l', body_opt, design_opt).mirror()

        # Torso
        self.ftorso = BodiceFront('ftorso', body_opt, design_opt).translate_by([0, 0, 20])
        self.btorso = TorsoPanel('btorso', body_opt, design_opt).translate_by([0, 0, -20])

        # Order of edges updated after (autonorm)..
        # TODO Simplify the choice of the edges to project from/to (regardless of autonorm)
        # _, fr_sleeve_int = pyp.ops.cut_corner(self.r_sleeve.interfaces[0].projecting_edges(), self.ftorso.right, 2, 3)
        # _, fl_sleeve_int = pyp.ops.cut_corner(self.l_sleeve.interfaces[0].projecting_edges(), self.ftorso.left, 4 + 3, 5 + 3)
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
            # (self.r_sleeve.interfaces[0], fr_sleeve_int),
            # (self.l_sleeve.interfaces[0], fl_sleeve_int),
            (self.r_sleeve.interfaces[1], br_sleeve_int),
            (self.l_sleeve.interfaces[1], bl_sleeve_int),

        )

        # DEBUG
        print('After connecting: ')
        print(self.btorso.interfaces[0])
        print(self.btorso.interfaces[3])