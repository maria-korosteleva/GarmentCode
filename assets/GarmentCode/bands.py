# Custom
import pypattern as pyp


class WBPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyp.esf.from_verts([0,0], [0, 10], [35, 10], [35, 0], loop=True)

        # define interface
        self.interfaces.append(pyp.Interface(self, self.edges[0]))
        self.interfaces.append(pyp.Interface(self, self.edges[1]))
        self.interfaces.append(pyp.Interface(self, self.edges[2]))
        self.interfaces.append(pyp.Interface(self, self.edges[3]))

        # Default translation
        self.center_x()


class WB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = WBPanel('wb_front')
        self.front.translate_by([0, -2, 20])
        self.back = WBPanel('wb_back')
        self.back.translate_by([0, -2, -15])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        )

        self.interfaces = [
            self.front.interfaces[3],
            self.back.interfaces[3]
        ]

