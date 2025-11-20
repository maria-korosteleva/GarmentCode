from typing import Optional, Any

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
    
    # Panel placement constants
    FRONT_TRANSLATION_Z: int = 20
    BACK_TRANSLATION_Z: int = -15
    
    # Class attributes
    waistband_design: WaistbandDesign
    waist: float
    waist_back: float
    waist_front: float
    width: float
    rise: float
    front: StraightBandPanel
    back: StraightBandPanel
    
    def __init__(
        self,
        waistband_design: WaistbandDesign,
        waist: float,
        waist_back: float,
        waist_front: float,
        rise: float = 1.0
    ) -> None:
        """Initialize a simple 2 panel waistband.
        
        Parameters:
        -----------
        waistband_design : WaistbandDesign
            Waistband design parameters object.
        waist : float
            Total waist measurement (full circumference).
        waist_back : float
            Back waist width measurement.
        waist_front : float
            Front waist width measurement (waist - waist_back).
        rise : float, optional
            The rise value of the bottoms that the WB is attached to.
            Adapts the shape of the waistband to sit tight on top of the given
            rise level (top measurement). If 1.0 or anything less than waistband width,
            the rise is ignored and the StraightWB is created to sit well on the waist.
            Default is 1.0.
        """
        super().__init__(body=None, design=None, rise=rise)

        # Store design and measurements
        self.waistband_design = waistband_design
        self.waist = waist
        self.waist_back = waist_back
        self.waist_front = waist_front
        self.width = self.waistband_design.width
        self.rise = rise

        self.define_panels()

        # Panels positioned at Y=0, will be moved in apply_body_alignment
        self.front.translate_by([0, 0, self.FRONT_TRANSLATION_Z])
        self.back.translate_by([0, 0, self.BACK_TRANSLATION_Z]) 
        
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
        """Define the front and back panels for the waistband.
        
        Both panels use the same horizontal width (max of front and back) to ensure
        they appear the same size. The difference in waist measurements is handled
        through ruffles on the interfaces.
        """
        # Use the larger width so both panels are the same size
        panel_width = max(self.waist_front, self.waist_back)
        
        self.front = StraightBandPanel(
            'wb_front',
            panel_width,
            self.width,
            match_int_proportion=self.waist_front
        )
        
        self.back = StraightBandPanel(
            'wb_back',
            panel_width,
            self.width,
            match_int_proportion=self.waist_back
        )
    
    def apply_body_alignment(self, body: BodyDefinition) -> None:
        """Apply body alignment to position the waistband correctly.
        
        Translates the waistband garment vertically based on the body's waist
        level to ensure proper fit and alignment.
        
        Parameters
        ----------
        body : BodyDefinition
            Body measurements object containing body parameters.
            Required parameters:
            - computed_waist_level: Vertical position of the waist level (computed property)
        """
        waist_level = body.computed_waist_level
        
        # Position front and back panels at waist level
        self.front.translate_by([0, waist_level, 0])
        self.back.translate_by([0, waist_level, 0])


class FittedWB(StraightWB):
    """Also known as Yoke: a waistband that follows the body curvature and sits tight.
    
    Made out of two circular arc panels.
    """
    
    # Class attributes
    hips: float
    hips_back: float
    hips_front: float
    waist_back_frac: float
    waist_front_frac: float
    hips_back_frac: float
    hips_front_frac: float
    bottom_width: float
    bottom_back_fraction: float
    
    def __init__(
        self,
        waistband_design: WaistbandDesign,
        waist: float,
        waist_back: float,
        waist_front: float,
        hips: float,
        hips_back: float,
        rise: float = 1.0
    ) -> None:
        """Initialize a waistband that follows the body curvature and sits tight.
        
        Parameters:
        -----------
        waistband_design : WaistbandDesign
            Waistband design parameters object.
        waist : float
            Total waist measurement (full circumference).
        waist_back : float
            Back waist width measurement.
        waist_front : float
            Front waist width measurement (waist - waist_back).
        hips : float
            Total hip measurement (full circumference).
        hips_back : float
            Back hip width measurement.
        rise : float, optional
            The rise value of the bottoms that the WB is attached to.
            Adapts the shape of the waistband to sit tight on top of the given
            rise level. If 1.0 or anything less than waistband width, the rise is
            ignored and the FittedWB is created to sit well on the waist.
            Default is 1.0.
        """
        # Store additional measurements for fitted waistband
        self.hips = hips
        self.hips_back = hips_back
        self.hips_front = hips - hips_back
        
        # Calculate fractions
        self.waist_back_frac = waist_back / waist if waist > 0 else 0.5
        self.waist_front_frac = waist_front / waist if waist > 0 else 0.5
        self.hips_back_frac = hips_back / hips if hips > 0 else 0.5
        self.hips_front_frac = self.hips_front / hips if hips > 0 else 0.5
        
        super().__init__(waistband_design, waist, waist_back, waist_front, rise)

    def define_panels(self) -> None:
        """Define the front and back circular arc panels for the fitted waistband."""
        # Calculate bottom width and fractions based on rise
        self.bottom_width = pyg.utils.lin_interpolation(
            self.hips, self.waist, self.rise
        )
        self.bottom_back_fraction = pyg.utils.lin_interpolation(
            self.hips_back_frac, self.waist_back_frac, self.rise
        )
        
        # Top width is the waist
        top_width = self.waist
        
        self.front = CircleArcPanel.from_all_length(
            'wb_front', 
            self.width, 
            top_width * self.waist_front_frac, 
            self.bottom_width * (1 - self.bottom_back_fraction),
            match_top_int_proportion=self.waist_front,
            match_bottom_int_proportion=self.waist_front
        )
        
        self.back = CircleArcPanel.from_all_length(
            'wb_back', 
            self.width, 
            top_width * self.waist_back_frac, 
            self.bottom_width * self.bottom_back_fraction,
            match_top_int_proportion=self.waist_back,
            match_bottom_int_proportion=self.waist_back
        )


class CuffBand(BaseBand):
    """Cuff class for sleeves or pants - band-like piece of fabric with optional skirt."""
    
    # Class attributes
    design: dict
    front: StraightBandPanel
    back: StraightBandPanel
    
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
    
    # Class attributes
    design: dict
    front: Any  # SkirtPanel type
    back: Any  # SkirtPanel type
    
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
    
    # Class attributes
    cuff: CuffBand
    skirt: CuffSkirt
    
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