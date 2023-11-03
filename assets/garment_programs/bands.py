import pypattern as pyp
from assets.garment_programs.circle_skirt import CircleArcPanel
from assets.garment_programs import skirt_paneled


class StraightBandPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name, width, depth=10) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyp.EdgeSeqFactory.from_verts(
            [0, 0], [0, depth], [width, depth], [width, 0], loop=True)

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
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        self.waist = design['waistband']['waist']['v'] * body['waist']
        self.width = design['waistband']['width']['v'] * body['hips_line']

        # TODO flexible fractions of the waist
        self.front = StraightBandPanel('wb_front', self.waist / 2, self.width)
        self.front.translate_by([0, body['waist_level'], 20])  
        self.back = StraightBandPanel('wb_back', self.waist / 2, self.width)
        self.back.translate_by([0, body['waist_level'], -15])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom_f': self.front.interfaces['bottom'],  
            'bottom_b': self.back.interfaces['bottom'],

            
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],

            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'],
                self.back.interfaces['bottom']),
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], 
                self.back.interfaces['top']),
        }


class FittedWB(pyp.Component):
    """Also known as Yoke: a waistband that ~follows the body curvature, and 
    hence sits tight 
    
    Made out of two circular arc panels
    """
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        # FIXME the linear interpolation does not appear to fix the body curves that well
        # TODO Assymetric front-back panels! (back has stronger curvature change)


        self.waist = design['waistband']['waist']['v'] * body['waist']
        self.width = design['waistband']['width']['v'] * body['hips_line']

        hips = body['hips'] * design['waistband']['waist']['v']
        hip_line = body['hips_line']

        bottom_width = pyp.utils.lin_interpolation(self.waist, hips, self.width / hip_line)

        self.front = CircleArcPanel.from_all_length(
            'wb_front', 
            self.width, 
            self.waist / 2, 
            bottom_width / 2)
        self.front.translate_by([0, body['waist_level'], 20])  
        
        self.back = CircleArcPanel.from_all_length(
            'wb_back', 
            self.width, 
            self.waist / 2, 
            bottom_width / 2)     
        self.back.translate_by([0, body['waist_level'], -15])  

        # ---
        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # ---
        self.interfaces = {
            'bottom_f': self.front.interfaces['bottom'],  
            'bottom_b': self.back.interfaces['bottom'],

            
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],

            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], 
                self.back.interfaces['bottom']),
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], 
                self.back.interfaces['top']),
        }


class CuffBand(pyp.Component):
    """ Cuff class for sleeves or pants
        band-like piece of fabric with optional "skirt"
    """
    def __init__(self, tag, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['cuff']

        # TODO flexible fractions of the width
        self.front = StraightBandPanel(
            f'{tag}_cuff_f', design['b_width']['v'] / 2, 
            design['b_depth']['v'])
        self.front.translate_by([0, 0, 15])  
        self.back = StraightBandPanel(
            f'{tag}_cuff_b', design['b_width']['v'] / 2, 
            design['b_depth']['v'])
        self.back.translate_by([0, 0, -15])  

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], 
                self.back.interfaces['bottom']),
            'top_front': self.front.interfaces['top'],
            'top_back': self.back.interfaces['top'],
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], 
                self.back.interfaces['top']),
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
                self.front.interfaces['bottom'], 
                self.back.interfaces['bottom']),
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
