# Custom
import pypattern as pyp
from . import skirt_paneled


class BandPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name, width, depth=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyp.esf.from_verts([0,0], [0, depth], [width, depth], [width, 0], loop=True)

        # define interface
        self.interfaces = {
            'right': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[1]),
            'left': pyp.Interface(self, self.edges[2]),
            'bottom': pyp.Interface(self, self.edges[3])
        }

        # Default translation
        self.top_center_pivot()
        self.center_x()


class WB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        self.waist = design['waistband']['waist']['v']
        self.width = design['waistband']['width']['v']

        # TODO flexible fractions of the waist
        self.front = BandPanel('wb_front', self.waist / 2, self.width)
        self.front.translate_by([0, body['waist_level'], 20])  
        self.back = BandPanel('wb_back', self.waist / 2, self.width)
        self.back.translate_by([0, body['waist_level'], -15])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom_f': self.front.interfaces['bottom'],   # TODO Remove these if the connected one does not work
            'bottom_b': self.back.interfaces['bottom'],

            
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],

            'bottom': pyp.Interface.from_multiple(self.front.interfaces['bottom'], self.back.interfaces['bottom']),
            'top': pyp.Interface.from_multiple(self.front.interfaces['top'], self.back.interfaces['top']),
        }



class CuffBand(pyp.Component):
    """ Cuff class for sleeves or pants
        band-like piece of fabric with optional "skirt"
    """
    def __init__(self, tag, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['cuff']

        # TODO flexible fractions of the width
        self.front = BandPanel(
            f'{tag}_cuff_f', design['b_width']['v'] / 2, design['b_depth']['v'] / 2)
        self.front.translate_by([0, 0, 10])  
        self.back = BandPanel(
            f'{tag}_cuff_b', design['b_width']['v'] / 2, design['b_depth']['v'] / 2)
        self.back.translate_by([0, 0, -10])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']),
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']),
        }

class CuffSkirt(pyp.Component):
    """A skirt-like flared cuff """

    def __init__(self, tag, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['cuff']
        width = design['b_width']['v']
        flare_diff = (design['skirt_flare']['v'] - 1) * width / 2

        self.front = skirt_paneled.SkirtPanel(
            f'{tag}_cuff_skirt_f', ruffles=design['skirt_ruffle']['v'], 
            waist_length=width, length=design['skirt_length']['v'], 
            flare=flare_diff)
        self.front.translate_by([0, 0, 10])  
        self.back = skirt_paneled.SkirtPanel(
            f'{tag}_cuff_skirt_b', ruffles=design['skirt_ruffle']['v'], 
            waist_length=width, length=design['skirt_length']['v'], 
            flare=flare_diff)
        self.back.translate_by([0, 0, -10])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']),
        }

# TODO 
class CuffBandSkirt(pyp.Component):
    """ Cuff class for sleeves or pants
        band-like piece of fabric with optional "skirt"
    """
    def __init__(self, tag, design) -> None:
        super().__init__(self.__class__.__name__)

        self.cuff = CuffBand(tag, design)
        self.skirt = CuffSkirt(tag, design)

        self.stitching_rules = pyp.Stitches(
            (self.cuff.interfaces['bottom'], self.skirt.interfaces['top']),
        )

        self.interfaces = {
            'top': self.cuff.interfaces['top']
        }