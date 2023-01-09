# Custom
import pypattern as pyp


class WBPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name, waist, width=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyp.esf.from_verts([0,0], [0, width], [waist, width], [waist, 0], loop=True)

        # define interface
        self.interfaces = {
            'right': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[1]),
            'left': pyp.Interface(self, self.edges[2]),
            'bottom': pyp.Interface(self, self.edges[3])
        }

        # Default translation
        self.center_x()


class WB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self, waist, width) -> None:
        super().__init__(self.__class__.__name__)

        # TODO flexible fractions of the waist
        self.front = WBPanel('wb_front', waist / 2, width)
        self.front.translate_by([0, -2, 20])
        self.back = WBPanel('wb_back', waist / 2, width)
        self.back.translate_by([0, -2, -15])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom_f': self.front.interfaces['bottom'],
            'bottom_b': self.back.interfaces['bottom'],
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
        }

