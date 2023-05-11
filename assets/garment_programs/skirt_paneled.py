# Custom
import pypattern as pyp
from scipy.spatial.transform import Rotation as R
import numpy as np

# other assets
from .bands import WB

# Panels
class SkirtPanel(pyp.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, waist_length=70, length=70, ruffles=1, bottom_cut=0, flare=0) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        top_width = base_width * ruffles
        low_width = top_width + 2*flare
        x_shift_top = (low_width - top_width) / 2  # to account for flare at the bottom

        # define edge loop
        self.right = pyp.esf.side_with_cut([0,0], [x_shift_top, length], start_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.Edge([0,0], [x_shift_top, length]))
        self.waist = pyp.Edge(self.right[-1].end, [x_shift_top + top_width, length])
        self.left = pyp.esf.side_with_cut(self.waist.end, [low_width, 0], end_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.Edge(self.waist.end, [low_width, 0]))
        self.bottom = pyp.Edge(self.left[-1].end, self.right[0].start)
        
        # define interface
        self.interfaces = {
            'right': pyp.Interface(self, self.right[-1]),
            'top': pyp.Interface(self, self.waist, ruffle=ruffles).reverse(True),
            'left': pyp.Interface(self, self.left[0]),
            'bottom': pyp.Interface(self, self.bottom)
        }
        # Single sequence for correct assembly
        self.edges = self.right
        self.edges.append(self.waist)  # on the waist
        self.edges.append(self.left)
        self.edges.append(self.bottom)

        # default placement
        self.top_center_pivot()
        self.center_x()  # Already know that this panel should be centered over Y


class ThinSkirtPanel(pyp.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10, bottom_width=20, length=70) -> None:
        super().__init__(name)

        # define edge loop
        self.flare = (bottom_width - top_width) / 2
        self.edges = pyp.esf.from_verts(
            [0,0], [self.flare, length], [self.flare + top_width, length], [self.flare * 2 + top_width, 0], 
            loop=True)

        # w.r.t. top left point
        self.set_pivot(self.edges[0].end)

        self.interfaces = {
            'right': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[1]),
            'left': pyp.Interface(self, self.edges[2])
        }

# TODOLOW front more narrow then the back
# TODO Fix dependent (Godet) skirt
class FittedSkirtPanel(pyp.Panel):
    """Fitted panel for a pencil skirt
    """
    def __init__(
        self, name, waist, hips,   # TODO Half measurement instead of a quarter
        hips_depth, length, low_width, rise=1,
        low_angle=0,
        dart_position=None,  dart_frac=0.5,
        cut=0,
        ruffle=False) -> None:
        # TODOLOW Only the parameters that differ between front/back panels?
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
            
            * rise -- the pant rize. 1 = waistline, 0 = crotch line (I'd not recommend to go all the way to zero 😅)
            * dart_position -- from the center of the body to the dart
            * ruffle -- use ruffles instead of fitting with darts. If ruffle = False, the dart_position needs to be specified
            * crotch_extention amount of exta fabric between legs
        """
        super().__init__(name)

        # adjust for a rise
        adj_crotch_depth = rise * hips_depth
        adj_waist = hips - rise * (hips - waist)
        dart_depth = hips_depth * dart_frac
        dart_depth = max(dart_depth - (hips_depth - adj_crotch_depth), 0)

        # eval shape
        # Check for ruffle
        if ruffle:
            ruffle_rate = hips / adj_waist
            adj_waist = hips 
        else:
            ruffle_rate = 1

        # amount of extra fabric
        w_diff = hips - adj_waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = w_diff / 6

        # Adjust the bottom edge to the desired angle
        angle_shift = np.tan(np.deg2rad(low_angle)) * low_width

        right = pyp.esf.curve_from_extreme(
            [hips - low_width, angle_shift],    
            [hw_shift, length + adj_crotch_depth],
            target_extreme=[0, length]
        )
        top = pyp.Edge(right.end, [hips * 2 - hw_shift, length + adj_crotch_depth])
        left = pyp.esf.curve_from_extreme(
            top.end,
            [hips + low_width, -angle_shift],
            target_extreme=[hips * 2, length]
        )
        self.edges = pyp.EdgeSequence(right, top, left).close_loop()
        bottom = self.edges[-1]

        if cut:  # add a cut
            # Use long and thin disconnected dart for a cutout
            new_edges, _, int_edges = pyp.ops.cut_into_edge(
                pyp.esf.dart_shape(1, cut),    # 1 cm  # TODOLOW width could also be a parameter?
                bottom, 
                offset= bottom.length() / 2,
                right=True)

            self.edges.substitute(bottom, new_edges)
            bottom = int_edges

        # Default placement
        self.top_center_pivot()
        self.translation = [-hips / 2, 5, 0]

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'bottom': pyp.Interface(self, bottom),
            'right': pyp.Interface(self, right), 
            'left': pyp.Interface(self, left),  
        }

        # Add top dart 
        if not ruffle and dart_depth: 
            # TODO: routine for multiple darts
            # FIXME front/back darts don't appear to be located at the same position
            dart_width = w_diff - hw_shift
            dart_shape = pyp.esf.dart_shape(dart_width, dart_depth)
            top_edge_len = top.length()
            top_edges, dart_edges, int_edges = pyp.ops.cut_into_edge(
                dart_shape, 
                top, 
                offset=(top_edge_len / 2 - dart_position),   # from the middle of the edge
                right=True)
            
            self.stitching_rules.append(
                (pyp.Interface(self, dart_edges[0]), pyp.Interface(self, dart_edges[1])))

            left_edge_len = top_edges[-1].length()
            top_edges_2, dart_edges, int_edges_2 = pyp.ops.cut_into_edge(
                dart_shape, 
                top_edges[-1], 
                offset=left_edge_len - top_edge_len / 2 + dart_position, # from the middle of the edge
                right=True)

            self.stitching_rules.append(
                (pyp.Interface(self, dart_edges[0]), pyp.Interface(self, dart_edges[1])))
            
            # Update panel
            top_edges.substitute(-1, top_edges_2)
            int_edges.substitute(-1, int_edges_2)

            self.interfaces['top'] = pyp.Interface(self, int_edges) 
            self.edges.substitute(top, top_edges)

            # Second dart

        else: 
            self.interfaces['top'] = pyp.Interface(self, self.edges[1], ruffle=ruffle_rate)   

class PencilSkirt(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['pencil-skirt']
        self.design = design  # Make accessible from outside

        # Depends on leg length
        # TODO Calculated Body parameter
        leg_length = body['height'] - body['head_l'] - body['waist_line'] - body['hips_line']
        length = body['hips_line'] * design['rise']['v'] + design['length']['v'] * leg_length

        self.front = FittedSkirtPanel(
            f'skirt_f',   
            body['waist'] / 4, 
            body['hips'] / 4, 
            body['hips_line'],
            length,
            low_width=design['flare']['v'] * body['hips'] / 4,
            rise=design['rise']['v'],
            low_angle=design['low_angle']['v'],
            dart_position=body['bust_points'] / 2,
            dart_frac=1.7,  # Diff for front and back
            ruffle=design['ruffle']['v'][0], 
            cut=design['front_cut']['v']
        ).translate_to([0, body['waist_level'], 25])
        self.back = FittedSkirtPanel(
            f'skirt_b', 
            body['waist'] / 4, 
            body['hips'] / 4,
            body['hips_line'],
            length,
            low_width=design['flare']['v'] * body['hips'] / 4,
            rise=design['rise']['v'],
            low_angle=design['low_angle']['v'],
            dart_position=body['bum_points'] / 2,
            dart_frac=1.1,   
            ruffle=design['ruffle']['v'][1],
            cut=design['back_cut']['v']
        ).translate_to([0, body['waist_level'], -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top'].reverse()
            ),
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }


# Full garments - Components
class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self, body, design, tag='') -> None:
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')

        design = design['skirt']

        self.front = SkirtPanel(
            f'front_{tag}' if tag else 'front', 
            waist_length=body['waist'], 
            length=design['length']['v'],
            ruffles=design['ruffle']['v'],   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v']
        ).translate_to([0, body['waist_level'], 25])
        self.back = SkirtPanel(
            f'back_{tag}'  if tag else 'back', 
            waist_length=body['waist'], 
            length=design['length']['v'],
            ruffles=design['ruffle']['v'],   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v']
        ).translate_to([0, body['waist_level'], -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']
            ),
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }

# With waistband
class SkirtWB(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        self.wb = WB(body, design)
        self.skirt = Skirt2(body, design)
        self.skirt.place_below(self.wb)

        self.stitching_rules = pyp.Stitches(
            (self.wb.interfaces['bottom'], self.skirt.interfaces['top'])
        )
        self.interfaces = {
            'top': self.wb.interfaces['top'],
            'bottom': self.skirt.interfaces['bottom']
        }


class SkirtManyPanels(pyp.Component):
    """Round Skirt with many panels"""

    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}_{design["flare-skirt"]["n_panels"]["v"]}')

        waist = body['waist']    # Fit to waist

        design = design['flare-skirt']
        n_panels = design['n_panels']['v']

        # Length is dependent on a height of a person
        length = body['hips_line'] + design['length']['v'] * (body['waist_level'] - body['hips_line'])

        flare_coeff_pi = 1 + design['suns']['v'] * length * 2 * np.pi / waist

        self.front = ThinSkirtPanel('front', panel_w:=waist / n_panels,
                                    bottom_width=panel_w * flare_coeff_pi,
                                    length=length )
        self.front.translate_to([-waist / 4, body['waist_level'], 0])
        # Align with a body
        self.front.rotate_by(R.from_euler('XYZ', [0, -90, 0], degrees=True))
        self.front.rotate_align([-waist / 4, 0, panel_w / 2])
        
        # Create new panels
        self.subs = pyp.ops.distribute_Y(self.front, n_panels, odd_copy_shift=15)

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces['left'], self.subs[i].interfaces['right']))
            
        self.stitching_rules.append((self.subs[-1].interfaces['left'], self.subs[0].interfaces['right']))

        # Define the interface
        self.interfaces = {
            'top': pyp.Interface.from_multiple(*[sub.interfaces['top'] for sub in self.subs])
        }

class SkirtManyPanelsWB(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        wb_width = 5
        self.skirt = SkirtManyPanels(body, design).translate_by([0, -wb_width, 0])
        self.wb = WB(body, design).translate_by([0, wb_width, 0])

        self.stitching_rules.append(
            (self.skirt.interfaces['top'], self.wb.interfaces['bottom']))


