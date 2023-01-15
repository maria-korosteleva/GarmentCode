# Custom
import pypattern as pyp
from scipy.spatial.transform import Rotation as R

# other assets
from .bands import WB

# TODO Skirt that fixes/hugs the hip area 
# TODO More modifications are needed to create pencil skirt though
class SkirtPanel(pyp.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, ruffles=1.5, waist_length=70, length=70, bottom_cut=20, flare=20) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        top_width = base_width * ruffles
        low_width = base_width + 2*flare
        x_shift_top = (low_width - top_width) / 2  # to account for flare at the bottom

        # define edge loop
        self.right = pyp.esf.side_with_cut([0,0], [x_shift_top, length], start_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.Edge([0,0], [x_shift_top, length]))
        self.waist = pyp.Edge(self.right[-1].end, [x_shift_top + top_width, length])
        self.left = pyp.esf.side_with_cut(self.waist.end, [low_width, 0], end_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.Edge(self.waist.end, [low_width, 0]))
        self.bottom = pyp.Edge(self.left[-1].end, self.right[0].start)
        
        # define interface
        self.interfaces = {
            'right': pyp.Interface(self, self.right[-1]),
            'top': pyp.Interface(self, self.waist, ruffle=ruffles),
            'left': pyp.Interface(self, self.left[0])
        }
        # Single sequence for correct assembly
        self.edges = self.right
        self.edges.append(self.waist)  # on the waist
        self.edges.append(self.left)
        self.edges.append(self.bottom)

        # default placement
        self.center_x()  # Already know that this panel should be centered over Y
        self.translation[1] = - length - 10


class ThinSkirtPanel(pyp.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10) -> None:
        super().__init__(name)

        # TODO parameterization
        # define edge loop
        length = 70
        self.flare = 10
        self.edges = pyp.esf.from_verts(
            [0,0], [self.flare, length], [self.flare + top_width, length], [self.flare * 2 + top_width, 0], loop=True)

        # w.r.t. 
        self.set_pivot(self.edges[0].end)

        self.interfaces = {
            'right': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[1]),
            'left': pyp.Interface(self, self.edges[2])
        }

        self.translation = [0, -length, 0]


class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self, ruffle_rate=1, flare=20) -> None:
        super().__init__(self.__class__.__name__)

        self.front = SkirtPanel('front', ruffle_rate, flare=flare).translate_by([0, 0, 20])
        self.back = SkirtPanel('back', ruffle_rate, flare=flare).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top']
        }


# With waistband
class SkirtWB(pyp.Component):
    def __init__(self, ruffle_rate=1.5, flare=20) -> None:
        super().__init__(f'{self.__class__.__name__}_{ruffle_rate:.1f}')

        self.wb = WB(waist=70, width=10)
        self.skirt = Skirt2(ruffle_rate=ruffle_rate, flare=flare)

        self.stitching_rules = pyp.Stitches(
            (self.wb.interfaces['bottom_f'], self.skirt.interfaces['top_f']),
            (self.wb.interfaces['bottom_b'], self.skirt.interfaces['top_b'])
        )


class SkirtManyPanels(pyp.Component):
    """Round Skirt with many panels"""

    def __init__(self, body, n_panels = 4) -> None:
        super().__init__(f'{self.__class__.__name__}_{n_panels}')

        self.n_panels = n_panels

        waist = body['waist']
        self.front = ThinSkirtPanel('front', waist / n_panels)
        self.front.translate_by([-waist / 4, body['height'] - body['head_l'] - body['waist_line'], 0])
        self.front.rotate_by(R.from_euler('XYZ', [0, 90, 0]))

        # TODO collisions
        self.subs = pyp.ops.distribute_Y(self.front, n_panels)

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces['left'], self.subs[i].interfaces['right']))
            
        self.stitching_rules.append((self.subs[-1].interfaces['left'], self.subs[0].interfaces['right']))

        self.interfaces = {'top': pyp.Interface.from_multiple(*[sub.interfaces['top'] for sub in self.subs])}


class SkirtManyPanelsWB(pyp.Component):
    def __init__(self, body, n_panels = 4) -> None:
        super().__init__(f'{self.__class__.__name__}_{n_panels}')

        wb_width = 5
        self.skirt = SkirtManyPanels(body, n_panels=n_panels).translate_by([0, -wb_width, 0])
        self.wb = WB(body['waist'], wb_width).translate_by([0, body['height'] - body['head_l'] - body['waist_line'], 0])

        self.stitching_rules.append(
            (self.skirt.interfaces['top'], self.wb.interfaces['bottom']))


