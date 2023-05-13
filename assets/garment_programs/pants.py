# Custom
import pypattern as pyp

# other assets
from . import bands


# TODO different fit in thights and  ankles
# TODO Add ease
class PantPanel(pyp.Panel):
    def __init__(
        self, name, waist, pant_width, 
        hips_depth,
        crotch_depth, 
        length, 
        rise=1,
        dart_position=None, ruffle=False, crotch_extention=5, crotch_angle_adj=1.) -> None:
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
            
            * rise -- the pant rize. 1 = waistline, 0 = crotch line (I'd not recommend to go all the way to zero 😅)
            * dart_position -- from the center of the body to the dart
            * ruffle -- use ruffles instead of fitting with darts. If ruffle = False, the dart_position needs to be specified
            * crotch_extention amount of exta fabric between legs
        """
        super().__init__(name)

        # adjust for a rise
        # NOTE crotch_depth is not properly used
        crotch_depth = crotch_depth - crotch_extention
        # DRAFT adj_crotch_depth = rise * crotch_depth
        adj_crotch_depth = rise * hips_depth
        adj_waist = pant_width - rise * (pant_width - waist)
        dart_depth = adj_crotch_depth * 0.8
        # DRAFT dart_depth = crotch_depth * 0.6  
        # DRAFT dart_depth = max(dart_depth - (crotch_depth - adj_crotch_depth), 0)

        # eval pants shape
        hips = pant_width + 2 * crotch_extention
        default_width = pant_width  
        # Check for ruffle
        if ruffle: 
            ruffle_rate = default_width / adj_waist
            adj_waist = default_width 
        else:
            ruffle_rate = 1

        # amount of extra fabric at waist
        w_diff = default_width - adj_waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = w_diff / 3
        
        # DRAFT
        # self.edges = pyp.esf.from_verts(
        #     [0, adj_crotch_depth - dart_depth],
        #     [hw_shift, adj_crotch_depth], 
        #     [w_diff + adj_waist, adj_crotch_depth],
        #     [w_diff + adj_waist, crotch_extention * crotch_angle_adj],
        #     [hips, 0],
        #     [hips - crotch_extention, - crotch_extention],
        #     [hips - crotch_extention, -length],
        #     [hips - 2*crotch_extention - pant_width, -length],
        #     loop=True
        # )

        # DRAFT 
        low_width = hips * 0.7   # TODO Parameter
        right = pyp.esf.curve_from_extreme(
            [(hips - low_width) / 2, 0],    
            [hw_shift, length + adj_crotch_depth],
            target_extreme=[0, length]
        )

        top = pyp.Edge(right.end, [w_diff + adj_waist, length + adj_crotch_depth])

        crotch = pyp.CurveEdge(
            top.end,
            [hips + crotch_extention, length - 8],   # TODO Placement?
            [[0.8, -0.4]]
        )

        left = pyp.CurveEdge(
            crotch.end,
            [hips - (hips - low_width) / 2, 0],   # TODO Placement?
            [[0.2, -0.2]]
        )

        self.edges = pyp.EdgeSequence(right, top, crotch, left).close_loop()
        bottom = self.edges[-1]

        # Default placement
        self.top_center_pivot()
        self.translation = [-hips / 2 - 0.5, 5, 0]

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'outside': pyp.Interface(self, right),
            'crotch': pyp.Interface(self, crotch),
            'inside': pyp.Interface(self, left),
            'bottom': pyp.Interface(self, bottom)
        }

        # FIXME Version with ruffles
        # Add top dart 
        if not ruffle and dart_depth: 
            dart_width = w_diff - hw_shift
            dart_shape = pyp.esf.dart_shape(dart_width, dart_depth)
            top_edges, dart_edges, int_edges = pyp.ops.cut_into_edge(
                dart_shape, top, offset=(hw_shift + adj_waist - dart_position), right=True)

            self.edges.substitute(top, top_edges)
            self.stitching_rules.append((pyp.Interface(self, dart_edges[0]), pyp.Interface(self, dart_edges[1])))

            self.interfaces['top'] = pyp.Interface(self, int_edges)   
        else: 
            self.interfaces['top'] = pyp.Interface(self, top, ruffle=ruffle_rate)   

class PantsHalf(pyp.Component):
    def __init__(self, tag, body, design) -> None:
        super().__init__(tag)
        design = design['pants']

        # TODO assymmetric front/back
        # FIXME What did this length calculation mean??
        # length = design['length']['v'] * (body['waist_level'] - body['crotch_depth'] + design['crotch_extention']['v'])
        
        length = body['hips_line'] + design['length']['v'] * body['leg_length']
        width = design['width']['v'] * body['hips'] / 4
        self.front = PantPanel(
            f'pant_f_{tag}',   
            body['waist'] / 4, 
            width, 
            body['hips_line'],
            body['crotch_depth'],
            length,
            rise=design['rise']['v'],
            dart_position=body['bust_points'] / 2,
            ruffle=design['ruffle_front']['v'],
            crotch_extention=design['crotch_extention']['v'],
            crotch_angle_adj=2
            ).translate_by([0, body['waist_level'] - 5, 25])
        self.back = PantPanel(
            f'pant_b_{tag}', 
            body['waist'] / 4, 
            width,
            body['hips_line'],
            body['crotch_depth'],
            length,
            rise=design['rise']['v'],
            dart_position=body['bum_points'] / 2,
            ruffle=design['ruffle_back']['v'],
            crotch_extention=design['crotch_extention']['v'],
            crotch_angle_adj=1.5
            ).translate_by([0, body['waist_level'] - 5, -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['outside'], self.back.interfaces['outside']),
            (self.front.interfaces['inside'], self.back.interfaces['inside'])
        )

        # add a cuff
        if design['cuff']['type']['v']:
            cuff_class = getattr(bands, design['cuff']['type']['v'])
            self.cuff = cuff_class(tag, design)

            pant_bottom = pyp.Interface.from_multiple(
                    self.front.interfaces['bottom'], self.back.interfaces['bottom'])
            # Position
            self.cuff.place_by_interface(
                self.cuff.interfaces['top'],
                pant_bottom,
                gap=5
            )

            # Stitch
            self.stitching_rules.append((
                pant_bottom,
                self.cuff.interfaces['top'])
            )

        self.interfaces = {
            'crotch_f': self.front.interfaces['crotch'],
            'crotch_b': self.back.interfaces['crotch'],
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
        }

class Pants(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__('Pants')


        self.right = PantsHalf('r', body, design)
        self.left = PantsHalf('l', body, design).mirror()

        self.stitching_rules = pyp.Stitches(
            (self.right.interfaces['crotch_f'], self.left.interfaces['crotch_f']),
            (self.right.interfaces['crotch_b'], self.left.interfaces['crotch_b']),
        )

        self.interfaces = {
            'top_f': pyp.Interface.from_multiple(
                self.right.interfaces['top_f'], self.left.interfaces['top_f']),
            'top_b': pyp.Interface.from_multiple(
                self.right.interfaces['top_b'], self.left.interfaces['top_b']),
            # Some are reversed for correct connection
            'top': pyp.Interface.from_multiple(   # around the body starting from front right
                self.right.interfaces['top_f'],
                self.left.interfaces['top_f'].reverse(),
                self.left.interfaces['top_b'],   
                self.right.interfaces['top_b'].reverse()),
        }

class WBPants(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__('WBPants')

        self.pants = Pants(body, design)

        # pants top
        wb_len = (self.pants.interfaces['top_b'].projecting_edges().length() + 
                    self.pants.interfaces['top_f'].projecting_edges().length())

        self.wb = bands.WB(body, design)
        self.wb.translate_by([0, self.wb.width + 2, 0])

        self.stitching_rules = pyp.Stitches(
            (self.pants.interfaces['top'], self.wb.interfaces['bottom']),
        )

