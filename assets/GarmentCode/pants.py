# Custom
import pypattern as pyp

# other assets
from .bands import WB


class PantFront(pyp.Panel):
    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        waist = body['waist'] / 4
        hips = body['hips'] / 4
        crouch_depth = body['crouch_depth']

        length = design['length']['v']

        pant_width = hips - 5

        hw_diff = (hips - waist) / 2
        b_shift = 5
        self.edges = pyp.esf.from_verts(
            [0, 0],
            [hw_diff, crouch_depth], 
            [hw_diff + waist, crouch_depth],
            [hw_diff + waist, 5],
            [hips, 0],
            [hips - 5, - 5],
            [hips - 5 - b_shift, -length],
            [hips - 5 - b_shift - pant_width, -length],
            loop=True
        )
        self.translation = [-hips, -crouch_depth, 0]

        print(len(self.edges), self.edges)  # DEBUG

        self.interfaces = {
            'outside': pyp.Interface(self, pyp.EdgeSequence(self.edges[-1], self.edges[0])),
            'crouch': pyp.Interface(self, self.edges[2:4]),
            'inside': pyp.Interface(self, self.edges[4:6]),
        }

        print(self.interfaces)


class Pants(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__('Pants')

        design = design['pants']

        self.fr = PantFront('pant_fr', body, design).translate_by([0, 0, 25])
        self.fl = PantFront('pant_fl', body, design).translate_by([0, 0, 25]).mirror()

        self.br = PantFront('pant_br', body, design).translate_by([0, 0, -20])
        self.bl = PantFront('pant_bl', body, design).translate_by([0, 0, -20]).mirror()

        self.stitching_rules = pyp.Stitches(
            (self.fr.interfaces['outside'], self.br.interfaces['outside']),
            (self.fl.interfaces['outside'], self.bl.interfaces['outside']),

            (self.fr.interfaces['crouch'], self.fl.interfaces['crouch']),
            (self.br.interfaces['crouch'], self.bl.interfaces['crouch']),

            (self.fr.interfaces['inside'], self.br.interfaces['inside']),
            (self.fl.interfaces['inside'], self.bl.interfaces['inside']),

        )


