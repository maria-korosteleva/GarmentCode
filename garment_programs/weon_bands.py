from typing import Optional, Any, List

import pygarment as pyg
from loguru import logger
from assets.garment_programs.circle_skirt import CircleArcPanel
from assets.garment_programs import skirt_paneled
from garment_programs.base_classes import BaseBand
from garment_programs.garment_enums import InterfaceName
from garment_programs.garment_program_utils import AttachmentHandler
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.waistband_design import WaistbandDesign
from config import AttachmentConstraint

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
            InterfaceName.RIGHT: pyg.Interface(self, self.edges[0]),
            InterfaceName.TOP: pyg.Interface(self, 
                                 self.edges[1], 
                                 ruffle=width / match_int_proportion if match_int_proportion is not None else 1.
                                 ).reverse(True),
            InterfaceName.LEFT: pyg.Interface(self, self.edges[2]),
            InterfaceName.BOTTOM: pyg.Interface(self, 
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
            (self.front.interfaces[InterfaceName.RIGHT], self.back.interfaces[InterfaceName.RIGHT]),
            (self.front.interfaces[InterfaceName.LEFT], self.back.interfaces[InterfaceName.LEFT])
        )

        self.interfaces = {
            InterfaceName.BOTTOM_F: self.front.interfaces[InterfaceName.BOTTOM],  
            InterfaceName.BOTTOM_B: self.back.interfaces[InterfaceName.BOTTOM],

            InterfaceName.TOP_F: self.front.interfaces[InterfaceName.TOP],
            InterfaceName.TOP_B: self.back.interfaces[InterfaceName.TOP],

            InterfaceName.BOTTOM: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.BOTTOM],
                self.back.interfaces[InterfaceName.BOTTOM]),
            InterfaceName.TOP: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.TOP], 
                self.back.interfaces[InterfaceName.TOP]),
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
    
    @staticmethod
    def get_attachment_constraints() -> List[AttachmentConstraint]:
        """Get the list of attachment constraints for this waistband garment.
        
        Returns the attachment constraints required for simulating this waistband garment.
        Waistbands do not require any attachment constraints by default.
        
        Returns:
        --------
        List[AttachmentConstraint]
            An empty list (waistbands do not require attachment constraints).
        """
        return []
    
    def get_vertex_processor_callback(self):
        """Get the vertex processor callback for waistband attachment constraints.
        
        Waistbands do not require custom vertex processing, so this returns a default
        callback that uses generic constraint processing.
        
        Returns:
        --------
        Callable[[BoxMesh], None] | None
            A callback that handles constraints with default behavior.
        """
        return AttachmentHandler.create_default_vertex_processor(BaseBand)

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
            (self.front.interfaces[InterfaceName.RIGHT], self.back.interfaces[InterfaceName.RIGHT]),
            (self.front.interfaces[InterfaceName.LEFT], self.back.interfaces[InterfaceName.LEFT])
        )

        self.interfaces = {
            InterfaceName.BOTTOM: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.BOTTOM], 
                self.back.interfaces[InterfaceName.BOTTOM]),
            InterfaceName.TOP_FRONT: self.front.interfaces[InterfaceName.TOP],
            InterfaceName.TOP_BACK: self.back.interfaces[InterfaceName.TOP],
            InterfaceName.TOP: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.TOP], 
                self.back.interfaces[InterfaceName.TOP]),
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
            (self.front.interfaces[InterfaceName.RIGHT], self.back.interfaces[InterfaceName.RIGHT]),
            (self.front.interfaces[InterfaceName.LEFT], self.back.interfaces[InterfaceName.LEFT])
        )

        self.interfaces = {
            InterfaceName.TOP: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.TOP], self.back.interfaces[InterfaceName.TOP]),
            InterfaceName.TOP_FRONT: self.front.interfaces[InterfaceName.TOP],
            InterfaceName.TOP_BACK: self.back.interfaces[InterfaceName.TOP],
            InterfaceName.BOTTOM: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.BOTTOM], 
                self.back.interfaces[InterfaceName.BOTTOM]),
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
            (self.cuff.interfaces[InterfaceName.BOTTOM], self.skirt.interfaces[InterfaceName.TOP]),
        )

        self.interfaces = {
            InterfaceName.TOP: self.cuff.interfaces[InterfaceName.TOP],
            InterfaceName.TOP_FRONT: self.cuff.interfaces[InterfaceName.TOP_FRONT],
            InterfaceName.TOP_BACK: self.cuff.interfaces[InterfaceName.TOP_BACK],
            InterfaceName.BOTTOM: self.skirt.interfaces[InterfaceName.BOTTOM]
        }

    def length(self) -> float:
        """Return the total length of the cuff (band + skirt).
        
        Returns:
        --------
        float
            Total length of the cuff band and skirt combined.
        """
        return self.cuff.length() + self.skirt.length()