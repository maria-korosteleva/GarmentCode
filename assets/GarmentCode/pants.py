# Custom
import pypattern as pyp

# other assets
from .bands import WB


# TODO different fit in thighs and   
# TODO different rise
class PantPanel(pyp.Panel):
    def __init__(self, name, waist, pant_width, crouch_depth, length) -> None:
        super().__init__(name)

        crouch_extention = 5
        hips = pant_width + crouch_extention

        hw_diff = (hips - waist) / 2
        
        self.edges = pyp.esf.from_verts(
            [0, 0],
            [hw_diff, crouch_depth], 
            [hw_diff + waist, crouch_depth],
            [hw_diff + waist, crouch_extention],
            [hips, 0],
            [hips - crouch_extention, - crouch_extention],
            [hips, -length],
            [hips - pant_width, -length],
            loop=True
        )
        self.translation = [-hips, -crouch_depth, 0]

        self.interfaces = {
            'outside': pyp.Interface(self, pyp.EdgeSequence(self.edges[-1], self.edges[0])),
            'crouch': pyp.Interface(self, self.edges[2:4]),
            'inside': pyp.Interface(self, self.edges[4:6]),
        }


class PantsHalf(pyp.Component):
    def __init__(self, tag, body, design) -> None:
        super().__init__(tag)
        design = design['pants']

        self.front = PantPanel(
            f'pant_f_{tag}', 
            body['waist'] / 4, 
            body['hips'] / 4, 
            body['crouch_depth'],
            design['length']['v']
            ).translate_by([0, 0, 25])
        self.back = PantPanel(
            f'pant_b_{tag}', 
            body['waist'] / 4, 
            body['hips'] / 4, 
            body['crouch_depth'],
            design['length']['v']
            ).translate_by([0, 0, -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['outside'], self.back.interfaces['outside']),
            (self.front.interfaces['inside'], self.back.interfaces['inside'])
        )
        
        self.interfaces = {
            'crouch_f': self.front.interfaces['crouch'],
            'crouch_b': self.back.interfaces['crouch']

        }

class Pants(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__('Pants')


        self.right = PantsHalf('r', body, design)
        self.left = PantsHalf('l', body, design).mirror()

        self.stitching_rules = pyp.Stitches(

            (self.right.interfaces['crouch_f'], self.left.interfaces['crouch_f']),
            (self.right.interfaces['crouch_b'], self.left.interfaces['crouch_b']),

        )


