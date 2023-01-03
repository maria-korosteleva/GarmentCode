# Custom
import pypattern as pyp

# other assets
from .bands import WB

# TODO Skirt that fixes/hugs the hip area 
# TODO More modifications are needed to create pencil skirt though
class HipRuffleSkirtPanel(pyp.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, ruffles=1.5, waist_length=70, length=70, bottom_cut=10, flare=20) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        top_width = base_width * ruffles
        low_width = base_width + 2*flare
        x_shift_top = (low_width - top_width) / 2  # to account for flare at the bottom

        left = pyp.esf.side_with_cut([0,0], [flare, length], start_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.LogicalEdge([0,0], [flare, length]))
        self.edges = left
        # Modify vertex position to account for ruffles
        self.edges[-1].end[0] = x_shift_top

        waist = pyp.LogicalEdge(self.edges[-1].end, [x_shift_top + top_width, length])
        self.edges.append(waist)  # on the waist

        self.edges[-1].end[0] = flare + base_width
        e_id = len(self.edges) - 1

        right = pyp.esf.side_with_cut(self.edges[-1].end, [low_width, 0], end_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.LogicalEdge(self.edges[-1].end, [low_width, 0]))
        self.edges.append(right)
        self.edges[e_id].end[0] = x_shift_top + top_width  # back

        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.Interface(self, left[-1]))
        # Ruffles are created by the differences in edge length
        # NOTE ruffles are only created when connecting with something
        self.interfaces.append(pyp.Interface(self, waist))
        self.interfaces.append(pyp.Interface(self, right[0]))


class SkirtPanel(pyp.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, ruffles=1.5, waist_length=70, length=70, bottom_cut=20, flare=20) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        top_width = base_width * ruffles
        low_width = base_width + 2*flare
        x_shift_top = (low_width - top_width) / 2  # to account for flare at the bottom

        # define edge loop
        self.left = pyp.esf.side_with_cut([0,0], [x_shift_top, length], start_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.LogicalEdge([0,0], [x_shift_top, length]))
        self.waist = pyp.LogicalEdge(self.left[-1].end, [x_shift_top + top_width, length])
        self.right = pyp.esf.side_with_cut(self.waist.end, [low_width, 0], end_cut=bottom_cut / length) if bottom_cut else pyp.EdgeSequence(pyp.LogicalEdge(self.waist.end, [low_width, 0]))
        self.bottom = pyp.LogicalEdge(self.right[-1].end, self.left[0].start)
        
        # define interface
        self.interfaces.append(pyp.Interface(self, self.left[-1]))
        # Create ruffles by the differences in edge length
        # NOTE ruffles are only created when connecting with something
        self.interfaces.append(pyp.Interface(self, self.waist))
        self.interfaces.append(pyp.Interface(self, self.right[0]))

        # Single sequence for correct assembly
        self.edges = self.left
        self.edges.append(self.waist)  # on the waist
        self.edges.append(self.right)
        self.edges.append(self.bottom)

        # default placement
        self.center_x()  # Already know that this panel should be centered over Y
        self.translation[1] = - length - 10


class ThinSkirtPanel(pyp.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyp.esf.from_verts([0,0], [10, 70], [10 + top_width, 70], [20 + top_width, 0], loop=True)

        self.interfaces.append(pyp.Interface(self, self.edges[0]))
        self.interfaces.append(pyp.Interface(self, self.edges[1]))
        self.interfaces.append(pyp.Interface(self, self.edges[2]))


class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self, ruffle_rate=1, flare=20) -> None:
        super().__init__(self.__class__.__name__)

        self.front = SkirtPanel('front', ruffle_rate, flare=flare).translate_by([0, 0, 20])

        self.back = SkirtPanel('back', ruffle_rate, flare=flare).translate_by([0, 0, -15])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        )

        # TODO use dict for interface references?
        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = [
            self.front.interfaces[1],
            self.back.interfaces[1]
        ]  


# With waistband
class SkirtWB(pyp.Component):
    def __init__(self, ruffle_rate=1.5, flare=20) -> None:
        super().__init__(f'{self.__class__.__name__}_{ruffle_rate:.1f}')

        self.wb = WB()
        self.skirt = Skirt2(ruffle_rate=ruffle_rate, flare=flare)

        self.stitching_rules = pyp.Stitches(
            (self.wb.interfaces[0], self.skirt.interfaces[0]),
            (self.wb.interfaces[1], self.skirt.interfaces[1])
        )


class SkirtManyPanels(pyp.Component):
    """Round Skirt with many panels"""

    def __init__(self, n_panels = 4) -> None:
        super().__init__(f'{self.__class__.__name__}_{n_panels}')

        self.n_panels = n_panels

        self.front = ThinSkirtPanel('front', 72 / n_panels).translate_by([-72 / n_panels, -75, 20]).center_x()

        self.subs = pyp.ops.distribute_Y(self.front, n_panels)

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces[2], self.subs[i].interfaces[0]))
        self.stitching_rules.append((self.subs[-1].interfaces[2], self.subs[0].interfaces[0]))

        # No interfaces
