# Custom
import pypattern as pyp


class SleevePanel(pyp.Panel):
    """Simple panel for a sleeve with optional ruffles on the sholder connection"""

    def __init__(self, name, length=35, arm_width=30, ease=3, ruffle=1) -> None:
        super().__init__(name)

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
    def __init__(self, tag) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        # sleeves
        self.f_sleeve = SleevePanel(f'{tag}_f_sleeve').translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(f'{tag}_b_sleeve').translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces[0], self.b_sleeve.interfaces[0]),
            (self.f_sleeve.interfaces[2], self.b_sleeve.interfaces[2]),
        )

        self.interfaces = [
            self.f_sleeve.interfaces[1],
            self.b_sleeve.interfaces[1],
        ]

class RuffleSleeve(pyp.Component):
    """Very simple sleeve"""
    # TODO Make it work as ruffles from a sleeve definition!!
    def __init__(self, tag, ruffle_rate=1.5, arm_width=30) -> None:
        super().__init__(f'{self.__class__.__name__}_{tag}')

        # sleeves
        self.f_sleeve = SleevePanel(f'{tag}_f_sleeve', arm_width=arm_width, ruffle=ruffle_rate).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(f'{tag}_b_sleeve', arm_width=arm_width, ruffle=ruffle_rate).translate_by([0, 0, -15])

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

    def __init__(self, name, length=50, neck_w=15, sholder_w=40, c_depth=15, ease=3) -> None:
        super().__init__(name)

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

class TorsoFittedPanel(pyp.Panel):
    """Panel for the front of upper garments with darts to properly fit it to the shape"""

    def __init__(self, name, length=50, neck_w=15, sholder_w=40, c_depth=15, ease=3, d_width=4, d_depth=10, bust_line=30) -> None:
        super().__init__(name)

        width = sholder_w + ease
        sholder_top_l = (width - neck_w) / 2 
        dart_from_top = bust_line
        # TODO dart depends on measurements?
        self.edges, _, r_interface, r_dart_stitch = pyp.esf.side_with_dart(
            [0, 0], [0, length], 
            width=d_width, depth=d_depth, dart_position=(length - dart_from_top), 
            opening_angle=150,
            right=True, modify='both', 
            panel=self)

        self.edges.append(pyp.esf.from_verts(
            self.edges[-1].end, 
            [sholder_top_l, length], 
            [width / 2, length - c_depth], 
            [sholder_top_l + neck_w, length], 
            [width, length]))

        l_edge, _, l_interface, l_dart_stitch = pyp.esf.side_with_dart(
            self.edges[-1].end, [width, 0], 
            width=d_width, depth=d_depth, dart_position=dart_from_top, 
            opening_angle=150,
            right=True, modify='both',
            panel=self)
        self.edges.append(l_edge)
        self.edges.close_loop()

        # default placement
        self.translate_by([-width / 2, 30 - length, 0])

        # TODO Finding ids of edges is a pain..
        self.interfaces = [
            r_interface,
            pyp.Interface(self, self.edges[4]),
            pyp.Interface(self, self.edges[7]),
            l_interface,
        ]

        # Stitch the darts
        self.stitching_rules.append(r_dart_stitch)
        self.stitching_rules.append(l_dart_stitch)


# TODO condition T-Shirts to be fitted or not
class TShirt(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, length=45, sholder_w=40, ruffle_sleeve=False) -> None:
        name_with_params = f'{self.__class__.__name__}_l{length}_s{sholder_w}'
        super().__init__(name_with_params if not ruffle_sleeve else f'{name_with_params}_Ruffle_sl')

        # sleeves
        if ruffle_sleeve:
            self.r_sleeve = RuffleSleeve('r')
            self.l_sleeve = RuffleSleeve('l').mirror()
        else:
            self.r_sleeve = SimpleSleeve('r')
            self.l_sleeve = SimpleSleeve('l').mirror()

        # Torso
        self.ftorso = TorsoPanel('ftorso', length=length, sholder_w=sholder_w).translate_by([0, 0, 20])
        self.btorso = TorsoPanel('btorso', length=length, sholder_w=sholder_w).translate_by([0, 0, -20])

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

    def __init__(self, length=45, sholder_w=40, bust_line=30) -> None:
        name_with_params = f'{self.__class__.__name__}_l{length}_s{sholder_w}_b{bust_line}'
        super().__init__(name_with_params)

        # sleeves
        self.r_sleeve = SimpleSleeve('r')
        self.l_sleeve = SimpleSleeve('l').mirror()

        # Torso
        self.ftorso = TorsoFittedPanel('ftorso', length=length, sholder_w=sholder_w, d_width=5, d_depth=13, bust_line=bust_line).translate_by([0, 0, 20])
        self.btorso = TorsoPanel('btorso', length=length, sholder_w=sholder_w).translate_by([0, 0, -20])

        # Order of edges updated after (autonorm)..
        # TODO Simplify the choice of the edges to project from/to (regardless of autonorm)

        _, fr_sleeve_int = pyp.ops.cut_corner(self.r_sleeve.interfaces[0].projecting_edges(), self.ftorso, 8, 9)
        _, fl_sleeve_int = pyp.ops.cut_corner(self.l_sleeve.interfaces[0].projecting_edges(), self.ftorso, 4, 5)
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