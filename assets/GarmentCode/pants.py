# Custom
import pypattern as pyp

# other assets
from .bands import WB


# TODO different fit in thighs and   
# TODO different rise
class PantPanel(pyp.Panel):
    def __init__(self, name, waist, pant_width, crouch_depth, length, dart_position=None, ruffle=False, crouch_extention=5) -> None:
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
            * If ruffle = False, the dart_position needs to be specified

            * crouch_extention amount of exta fabric between legs
        """
        super().__init__(name)

        hips = pant_width + crouch_extention
        if ruffle:
            ruffle_rate = pant_width / waist
            waist = pant_width   # TODO Or default waist?
        else:
            ruffle_rate = 1

        # eval pants shape
        default_width = pant_width - crouch_extention / 2
        w_diff = default_width - waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 

        hw_shift = pant_width - waist - crouch_extention / 2    
        
        self.edges = pyp.esf.from_verts(
            [0, 0],
            [hw_shift, crouch_depth], 
            [hw_shift + waist, crouch_depth],
            [hw_shift + waist, crouch_extention],
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
            'top': pyp.Interface(self, self.edges[1], ruffle=ruffle_rate)   # TODO this one needs multi-panel stitch!
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


