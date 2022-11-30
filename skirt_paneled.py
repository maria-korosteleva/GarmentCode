import json
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from scipy.spatial.transform import Rotation as R

# Custom
import pypattern as pyp
from customconfig import Properties

# ------ Panels -------
class RuffleSkirtPanel(pyp.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, ruffles=1.5, waist_length=70, length=70) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        panel_top_width = base_width * ruffles
        panel_low_width = base_width + 40
        x_shift = (panel_low_width - panel_top_width) / 2

        # define edge loop
        self.edges = [pyp.LogicalEdge((0,0), (x_shift, length))]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (x_shift + panel_top_width, length)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (panel_low_width, 0)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.InterfaceInstance(self, 0))
        # Create ruffles by the differences in edge length
        # NOTE ruffles are only created when connecting with something
        self.interfaces.append(pyp.InterfaceInstance(self, 1, pyp.LogicalEdge((20, length), (20 + base_width, length))))
        self.interfaces.append(pyp.InterfaceInstance(self, 2))

class ThinSkirtPanel(pyp.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = [pyp.LogicalEdge((0,0), (10, 70))]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (10 + top_width, 70)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (20 + top_width, 0)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        self.interfaces.append(pyp.InterfaceInstance(self, 0))
        self.interfaces.append(pyp.InterfaceInstance(self, 1))
        self.interfaces.append(pyp.InterfaceInstance(self, 2))


class WBPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = [pyp.LogicalEdge((0,0), (0, 10))]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (35, 10)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (35, 0)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.InterfaceInstance(self, 0))
        self.interfaces.append(pyp.InterfaceInstance(self, 1))
        self.interfaces.append(pyp.InterfaceInstance(self, 2))
        self.interfaces.append(pyp.InterfaceInstance(self, 3))


# ------ Garments -------
class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self, ruffle_rate=1) -> None:
        super().__init__(self.__class__.__name__)

        self.front = RuffleSkirtPanel('front', ruffle_rate)
        self.front.translate_by([-40, -75, 20])
        self.front.swap_right_wrong()

        self.back = RuffleSkirtPanel('back', ruffle_rate)
        self.back.translate_by([-40, -75, -15])

        self.stitching_rules = [
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        ]

        # TODO use dict for interface references?
        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = [
            self.front.interfaces[1],
            self.back.interfaces[1]
        ]  


# With waistband
class WB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = WBPanel('wb_front')
        self.front.translate_by([-20, -2, 20])
        self.front.swap_right_wrong()
        self.back = WBPanel('wb_back')
        self.back.translate_by([-20, -2, -15])

        self.stitching_rules = [
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        ]

        self.interfaces = [
            self.front.interfaces[3],
            self.back.interfaces[3]
        ]


class SkirtWB(pyp.Component):
    def __init__(self, ruffle_rate=1.5) -> None:
        super().__init__(f'{self.__class__.__name__}_{ruffle_rate:.1f}')

        self.wb = WB()
        self.skirt = Skirt2(ruffle_rate=ruffle_rate)

        self.stitching_rules = [
            (self.wb.interfaces[0], self.skirt.interfaces[0]),
            (self.wb.interfaces[1], self.skirt.interfaces[1])
        ]


class SkirtManyPanels(pyp.Component):
    """Round Skirt with many panels"""

    def __init__(self, n_panels = 4) -> None:
        super().__init__(f'{self.__class__.__name__}_{n_panels}')

        self.n_panels = n_panels

        self.front = ThinSkirtPanel('front', 72 / n_panels)
        self.front.translate_by([-72 / n_panels, -75, 20])
        self.front.swap_right_wrong()

        self.subs = pyp.ops.distribute_Y(self.front, n_panels)

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces[2], self.subs[i].interfaces[0]))
        self.stitching_rules.append((self.subs[-1].interfaces[2], self.subs[0].interfaces[0]))

    def new_method(self, delta_rotation):
        return delta_rotation

        # No interfaces


if __name__ == '__main__':

    test_garments = [
        SkirtWB(1),
        SkirtWB(1.5),
        SkirtWB(2),
        # WB(),
        # Skirt2()
        SkirtManyPanels(n_panels=2),
        SkirtManyPanels(n_panels=4),
        SkirtManyPanels(n_panels=10)
    ]

    # test_garments[0].translate_by([2, 0, 0])

    for piece in test_garments:
        pattern = piece()

        # DEBUG 
        # print(json.dumps(pattern, indent=2, sort_keys=True))

        # Save as json file
        sys_props = Properties('./system.json')
        filename = pattern.serialize(
            Path(sys_props['output']), 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=False)

        print(f'Success! {piece.name} saved to {filename}')