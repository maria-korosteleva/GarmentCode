from copy import copy

# Custom
import pypattern as pyp

# other assets
from .sleeves import *


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


# TODO add collar variations
# TODO define as a half
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
