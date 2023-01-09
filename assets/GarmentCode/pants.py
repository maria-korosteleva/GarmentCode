# Custom
import pypattern as pyp

# other assets
from .bands import WB


# TODO different fit in thighs and  ankles
# TODO Add ease
class PantPanel(pyp.Panel):
    def __init__(
        self, name, waist, pant_width, 
        crouch_depth, length, rise=1,
        dart_position=None, dart_depth=10, ruffle=False, crouch_extention=5) -> None:
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
            
            * rise -- the pant rize. 1 = waistline, 0 = crouch line (I'd not recommend to go all the way to zero 😅)
            * dart_position -- from the center of the body to the dart
            * If ruffle = False, the dart_position and dart_depth need to be specified
            * crouch_extention amount of exta fabric between legs
        """
        super().__init__(name)

        # adjust for a rise
        adj_crouch_depth = rise * crouch_depth
        adj_waist = pant_width - rise * (pant_width - waist)

        # Check for ruffle
        if ruffle:  # TODO Try and debug
            ruffle_rate = pant_width / adj_waist
            adj_waist = pant_width   # TODO Or default waist?
        else:
            ruffle_rate = 1

        # eval pants shape
        hips = pant_width + crouch_extention
        default_width = pant_width - crouch_extention / 2
        w_diff = default_width - adj_waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 

        # hw_shift = pant_width - waist - crouch_extention / 2    
        hw_shift = w_diff / 3
        dart_width = w_diff - hw_shift
        
        self.edges = pyp.esf.from_verts(
            [0, 0],
            [hw_shift, adj_crouch_depth], 
            [hw_shift + adj_waist, adj_crouch_depth],
            [hw_shift + adj_waist, crouch_extention],
            [hips, 0],
            [hips - crouch_extention, - crouch_extention],
            [hips, -length],
            [hips - pant_width, -length],
            loop=True
        )

        # Default placement
        self.translation = [-hips, -crouch_depth, 0]

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'outside': pyp.Interface(self, pyp.EdgeSequence(self.edges[-1], self.edges[0])),
            'crouch': pyp.Interface(self, self.edges[2:4]),
            'inside': pyp.Interface(self, self.edges[4:6]),
        }

        # Add top dart 
        if dart_position is not None: 
            dart_shape = pyp.esf.dart_shape(dart_width, dart_depth)
            top_edges, dart_edges, int_edges = pyp.ops.cut_into_edge(
                dart_shape, self.edges[1], offset=(hw_shift + adj_waist - dart_position), right=True)

            self.edges.substitute(1, top_edges)
            self.stitching_rules.append((pyp.Interface(self, dart_edges[0]), pyp.Interface(self, dart_edges[1])))

            self.interfaces['top'] = pyp.Interface(self, int_edges)   
        else: 
            # TODO this one needs multi-panel stitch!]
            self.interfaces['top'] = pyp.Interface(self, self.edges[1], ruffle=ruffle_rate)   

class PantsHalf(pyp.Component):
    def __init__(self, tag, body, design) -> None:
        super().__init__(tag)
        design = design['pants']

        print(body['hips'] / 4)

        # TODO Ruffles on this level
        self.front = PantPanel(
            f'pant_f_{tag}',   
            body['waist'] / 4, 
            design['width']['v'], 
            body['crouch_depth'],
            design['length']['v'],
            rise=design['rise']['v'],
            dart_position=body['bust_points'] / 2,
            dart_depth=10,
            ).translate_by([0, 0, 25])
        self.back = PantPanel(
            f'pant_b_{tag}', 
            body['waist'] / 4, 
            body['hips'] / 4, 
            body['crouch_depth'],
            design['length']['v'],
            rise=design['rise']['v'],
            dart_position=body['bust_points'] / 2,
            dart_depth=10
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


