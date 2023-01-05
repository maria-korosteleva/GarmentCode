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
        self.f_sleeve = SleevePanel(f'{tag}_f', body_opt, design_opt).translate_by([0, 0, 15])
        self.b_sleeve = SleevePanel(f'{tag}_b', body_opt, design_opt).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.f_sleeve.interfaces[0], self.b_sleeve.interfaces[0]),
            (self.f_sleeve.interfaces[2], self.b_sleeve.interfaces[2]),
        )

        self.interfaces = [
            self.f_sleeve.interfaces[1],
            self.b_sleeve.interfaces[1],
        ]

# Armhole shapes withough sleeves
# TODO I need here the matching interface for interchengeability ..
def ArmholeSimple(tag, body, design):
    arm_width = body['arm_width']
    ease = design['sleeve']['ease']['v'] 
    width = (arm_width + ease) / 2

    edges = pyp.EdgeSequence(pyp.LogicalEdge([0, 0], [7, width]))
    
    return edges