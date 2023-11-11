# Custom
import pypattern as pyp
from . import skirt_paneled
from .circle_skirt import CircleArcPanel

class StraightBandPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name, width, depth=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyp.esf.from_verts([0,0], [0, depth], [width, depth], [width, 0], loop=True)

        # define interface
        self.interfaces = {
            'right': pyp.Interface(self, self.edges[0]),
            'top': pyp.Interface(self, self.edges[1]).reverse(True),
            'left': pyp.Interface(self, self.edges[2]),
            'bottom': pyp.Interface(self, self.edges[3])
        }

        # Default translation
        self.top_center_pivot()
        self.center_x()


class StraightWB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self, body, design, rise=1.) -> None:
        """Simple 2 panel waistband

            * rise -- the rise value of the bottoms that the WB is attached to 
                Adapts the shape of the waistband to sit tight on top 
                of the given rise level (top measurement). If 1. or anything less than waistband width, 
                the rise is ignored and the StraightWB is created to sit well on the waist
        
        """
        super().__init__(self.__class__.__name__)

        # Measurements
        self.waist = design['waistband']['waist']['v'] * body['waist']
        self.waist_back_frac = body['waist_back_width'] / body['waist']
        self.hips = body['hips'] * design['waistband']['waist']['v']
        self.hips_back_frac = body['hip_back_width'] / body['hips']

        # Params
        self.width = design['waistband']['width']['v'] 
        self.rise = rise
        # Check correct values
        if self.rise + self.width > 1:
            self.rise = 1 - self.width

        self.top_width = pyp.utils.lin_interpolation(
            self.hips, self.waist, self.rise + self.width)
        self.top_back_fraction = pyp.utils.lin_interpolation(
            self.hips_back_frac, self.waist_back_frac, self.rise + self.width)
        
        self.width = self.width * body['hips_line']

        self.define_panels()

        self.front.translate_by([0, body['_waist_level'], 20])
        self.back.translate_by([0, body['_waist_level'], -15]) 
        
        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom_f': self.front.interfaces['bottom'],  
            'bottom_b': self.back.interfaces['bottom'],

            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],

            'bottom': pyp.Interface.from_multiple(self.front.interfaces['bottom'], self.back.interfaces['bottom']),
            'top': pyp.Interface.from_multiple(self.front.interfaces['top'], self.back.interfaces['top']),
        }

    def define_panels(self):
        back_width = self.top_width * self.top_back_fraction

        # TODO check in 3D -- fitting to top or to the bottom of the lowered bottoms??
        self.front = StraightBandPanel(
            'wb_front', 
            self.top_width - back_width, 
            self.width)
          
        self.back = StraightBandPanel(
            'wb_back', 
            back_width, 
            self.width)

class FittedWB(StraightWB):
    """Also known as Yoke: a waistband that ~follows the body curvature, and hence sits tight
        Made out of two circular arc panels
    """
    def __init__(self, body, design, rise=1.) -> None:
        """A waistband that ~follows the body curvature, and hence sits tight
        
            * rise -- the rise value of the bottoms that the WB is attached to 
                Adapts the shape of the waistband to sit tight on top 
                of the given rise level. If 1. or anything less than waistband width, 
                the rise is ignored and the FittedWB is created to sit well on the waist
        """
        super().__init__(body, design, rise)

    def define_panels(self):
        self.bottom_width = pyp.utils.lin_interpolation(
            self.hips, self.waist, self.rise)
        self.bottom_back_fraction = pyp.utils.lin_interpolation(
            self.hips_back_frac, self.waist_back_frac, self.rise)
        
        self.front = CircleArcPanel.from_all_length(
            'wb_front', 
            self.width, 
            self.top_width * (1 - self.top_back_fraction), 
            self.bottom_width * (1 - self.bottom_back_fraction))
        
        self.back = CircleArcPanel.from_all_length(
            'wb_back', 
            self.width, 
            self.top_width * self.top_back_fraction, 
            self.bottom_width * self.bottom_back_fraction)     


class CuffBand(pyp.Component):
    """ Cuff class for sleeves or pants
        band-like piece of fabric with optional "skirt"
    """
    def __init__(self, tag, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['cuff']

        self.front = StraightBandPanel(
            f'{tag}_cuff_f', design['b_width']['v'] / 2, design['b_depth']['v'])
        self.front.translate_by([0, 0, 15])  
        self.back = StraightBandPanel(
            f'{tag}_cuff_b', design['b_width']['v'] / 2, design['b_depth']['v'])
        self.back.translate_by([0, 0, -15])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']),
            'top_front': self.front.interfaces['top'],
            'top_back': self.back.interfaces['top'],
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
        self.front.translate_by([0, 0, 15])  
        self.back = skirt_paneled.SkirtPanel(
            f'{tag}_cuff_skirt_b', ruffles=design['skirt_ruffle']['v'], 
            waist_length=width, length=design['skirt_length']['v'], 
            flare=flare_diff)
        self.back.translate_by([0, 0, -15])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']),
            'top_front': self.front.interfaces['top'],
            'top_back': self.back.interfaces['top'],
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']),
        }

class CuffBandSkirt(pyp.Component):
    """ Cuff class for sleeves or pants
        band-like piece of fabric with optional "skirt"
    """
    def __init__(self, tag, design) -> None:
        super().__init__(self.__class__.__name__)

        self.cuff = CuffBand(tag, design)
        self.skirt = CuffSkirt(tag, design)

        # Align
        self.skirt.place_below(self.cuff)

        self.stitching_rules = pyp.Stitches(
            (self.cuff.interfaces['bottom'], self.skirt.interfaces['top']),
        )

        self.interfaces = {
            'top': self.cuff.interfaces['top'],
            'top_front': self.cuff.interfaces['top_front'],
            'top_back': self.cuff.interfaces['top_back'],
            'bottom': self.skirt.interfaces['bottom']
        }