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


# Full garments - Components
class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['skirt']

        self.front = SkirtPanel(
            'front', 
            waist_length=body['waist'], 
            length=design['length']['v'],
            ruffles=design['ruffle']['v'],   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v']
        ).translate_to([0, body['waist_level'], 25])
        self.back = SkirtPanel(
            'back', 
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


