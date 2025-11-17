from typing import Optional

import pygarment as pyg
from assets.garment_programs.circle_skirt import CircleArcPanel
from assets.garment_programs import skirt_paneled
from garment_programs.base_classes import BaseBand
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.waistband_design import WaistbandDesign

class StraightBandPanel(pyg.Panel):
    """One panel for a panel skirt."""

    def __init__(
        self,
        name: str,
        width: float,
        depth: float,
        match_int_proportion: Optional[float] = None
    ) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = pyg.EdgeSeqFactory.from_verts(
            [0, 0], [0, depth], [width, depth], [width, 0], loop=True)

        # define interface
        self.interfaces = {
            'right': pyg.Interface(self, self.edges[0]),
            'top': pyg.Interface(self, 
                                 self.edges[1], 
                                 ruffle=width / match_int_proportion if match_int_proportion is not None else 1.
                                 ).reverse(True),
            'left': pyg.Interface(self, self.edges[2]),
            'bottom': pyg.Interface(self, 
                                    self.edges[3], 
                                    ruffle=width / match_int_proportion if match_int_proportion is not None else 1.
                                    )
        }

        # Default translation
        self.top_center_pivot()
        self.center_x()


class StraightWB(BaseBand):
    """Simple 2 panel waistband."""
    
    def __init__(
        self,
        body: BodyDefinition | dict,
        design: dict,
        waist: Optional[float] = None,
        waist_back: Optional[float] = None,
        rise: float = 1.0
    ) -> None:
        """Initialize a simple 2 panel waistband.
        
        Parameters:
        -----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary containing waistband specifications.
        waist : float, optional
            Waist width for the front panel. If None, will be calculated from body.
        waist_back : float, optional
            Waist width for the back panel. If None, will be calculated from body.
        rise : float, optional
            The rise value of the bottoms that the WB is attached to.
            Adapts the shape of the waistband to sit tight on top of the given
            rise level (top measurement). If 1.0 or anything less than waistband width,
            the rise is ignored and the StraightWB is created to sit well on the waist.
            Default is 1.0.
        """
        super().__init__(body, design, rise=rise)

        # Create WaistbandDesign from the design dict and store it
        self.waistband_design = WaistbandDesign(design)

        # Params
        self.waist = waist
        self.waist_back = waist_back
        self.width = self.waistband_design.width
        self.rise = rise

        self.define_panels()

        self.front.translate_by([0, body['_waist_level'], 20])
        self.back.translate_by([0, body['_waist_level'], -15]) 
        
        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom_f': self.front.interfaces['bottom'],  
            'bottom_b': self.back.interfaces['bottom'],

            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],

            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'],
                self.back.interfaces['bottom']),
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'], 
                self.back.interfaces['top']),
        }

    def define_panels(self) -> None:
        """Define the front and back panels for the waistband."""
        self.front = StraightBandPanel(
            'wb_front',
            self.waist,
            self.width,
            match_int_proportion=self.body['waist'] - self.body['waist_back_width']
        )
        
        self.back = StraightBandPanel(
            'wb_back',
            self.waist_back,
            self.width,
            match_int_proportion=self.body['waist_back_width']
        )


class FittedWB(StraightWB):
    """Also known as Yoke: a waistband that follows the body curvature and sits tight.
    
    Made out of two circular arc panels.
    """
    
    def __init__(
        self,
        body: BodyDefinition | dict,
        design: dict,
        rise: float = 1.0
    ) -> None:
        """Initialize a waistband that follows the body curvature and sits tight.
        
        Parameters:
        -----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary containing waistband specifications.
        rise : float, optional
            The rise value of the bottoms that the WB is attached to.
            Adapts the shape of the waistband to sit tight on top of the given
            rise level. If 1.0 or anything less than waistband width, the rise is
            ignored and the FittedWB is created to sit well on the waist.
            Default is 1.0.
        """
        self.bottom_width = None
        self.bottom_back_fraction = None
        super().__init__(body, design, rise)

    def define_panels(self) -> None:
        """Define the front and back circular arc panels for the fitted waistband."""
        self.bottom_width = pyg.utils.lin_interpolation(
            self.hips, self.waist, self.rise
        )
        self.bottom_back_fraction = pyg.utils.lin_interpolation(
            self.hips_back_frac, self.waist_back_frac, self.rise
        )
        
        self.front = CircleArcPanel.from_all_length(
            'wb_front', 
            self.width, 
            self.top_width * (1 - self.top_back_fraction), 
            self.bottom_width * (1 - self.bottom_back_fraction),
            match_top_int_proportion=self.body['waist'] - self.body['waist_back_width'],
            match_bottom_int_proportion=self.body['waist'] - self.body['waist_back_width']
        )
        
        self.back = CircleArcPanel.from_all_length(
            'wb_back', 
            self.width, 
            self.top_width * self.top_back_fraction, 
            self.bottom_width * self.bottom_back_fraction,
            match_top_int_proportion=self.body['waist_back_width'],
            match_bottom_int_proportion=self.body['waist_back_width']
        )


class CuffBand(BaseBand):
    """Cuff class for sleeves or pants - band-like piece of fabric with optional skirt."""
    
    def __init__(
        self,
        tag: str,
        design: dict,
        length: Optional[float] = None
    ) -> None:
        """Initialize a cuff band.
        
        Parameters:
        -----------
        tag : str
            Tag identifier for the cuff (e.g., 'sl_right' for sleeve left).
        design : dict
            Design parameters dictionary containing cuff specifications.
        length : float, optional
            Length of the cuff. If None, will be taken from design['cuff']['cuff_len']['v'].
        """
        super().__init__(body=None, design=design, tag=tag)

        self.design = design['cuff']

        if length is None:
            length = self.design['cuff_len']['v']

        self.front = StraightBandPanel(
            f'{tag}_cuff_f', self.design['b_width']['v'] / 2, length)
        self.front.translate_by([0, 0, 15])  
        self.back = StraightBandPanel(
            f'{tag}_cuff_b', self.design['b_width']['v'] / 2, length)
        self.back.translate_by([0, 0, -15])  

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'], 
                self.back.interfaces['bottom']),
            'top_front': self.front.interfaces['top'],
            'top_back': self.back.interfaces['top'],
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'], 
                self.back.interfaces['top']),
        }


class CuffSkirt(BaseBand):
    """A skirt-like flared cuff."""
    
    def __init__(
        self,
        tag: str,
        design: dict,
        length: Optional[float] = None
    ) -> None:
        """Initialize a skirt-like flared cuff.
        
        Parameters:
        -----------
        tag : str
            Tag identifier for the cuff skirt.
        design : dict
            Design parameters dictionary containing cuff specifications.
        length : float, optional
            Length of the cuff skirt. If None, will be taken from design['cuff']['cuff_len']['v'].
        """
        super().__init__(body=None, design=design, tag=tag)

        self.design = design['cuff']
        width = self.design['b_width']['v']
        flare_diff = (self.design['skirt_flare']['v'] - 1) * width / 2

        if length is None:
            length = self.design['cuff_len']['v']

        self.front = skirt_paneled.SkirtPanel(
            f'{tag}_cuff_skirt_f', ruffles=self.design['skirt_ruffle']['v'], 
            waist_length=width / 2, length=length, 
            flare=flare_diff)
        self.front.translate_by([0, 0, 15])  
        self.back = skirt_paneled.SkirtPanel(
            f'{tag}_cuff_skirt_b', ruffles=self.design['skirt_ruffle']['v'], 
            waist_length=width / 2, length=length, 
            flare=flare_diff)
        self.back.translate_by([0, 0, -15])  

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        self.interfaces = {
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']),
            'top_front': self.front.interfaces['top'],
            'top_back': self.back.interfaces['top'],
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'], 
                self.back.interfaces['bottom']),
        }


class CuffBandSkirt(pyg.Component):
    """Cuff class for sleeves or pants - band-like piece of fabric with optional skirt."""
    
    def __init__(self, tag: str, design: dict) -> None:
        """Initialize a combined cuff band and skirt.
        
        Parameters:
        -----------
        tag : str
            Tag identifier for the cuff.
        design : dict
            Design parameters dictionary containing cuff specifications.
        """
        super().__init__(self.__class__.__name__)

        self.cuff = CuffBand(
            tag, 
            design, 
            length=design['cuff']['cuff_len']['v'] * (1 - design['cuff']['skirt_fraction']['v'])
        )
        self.skirt = CuffSkirt(
            tag, 
            design, 
            length=design['cuff']['cuff_len']['v'] * design['cuff']['skirt_fraction']['v']
        )

        # Align
        self.skirt.place_below(self.cuff)

        self.stitching_rules = pyg.Stitches(
            (self.cuff.interfaces['bottom'], self.skirt.interfaces['top']),
        )

        self.interfaces = {
            'top': self.cuff.interfaces['top'],
            'top_front': self.cuff.interfaces['top_front'],
            'top_back': self.cuff.interfaces['top_back'],
            'bottom': self.skirt.interfaces['bottom']
        }

    def length(self) -> float:
        """Return the total length of the cuff (band + skirt).
        
        Returns:
        --------
        float
            Total length of the cuff band and skirt combined.
        """
        return self.cuff.length() + self.skirt.length()