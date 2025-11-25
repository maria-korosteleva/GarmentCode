"""Garment factory for creating garment instances.

This module implements a factory pattern for creating garment components,
replacing the dynamic class lookup approach used in MetaGarment.
"""

from typing import Union, Any

import pygarment as pyg
from loguru import logger

from garment_programs.weon_pants import Pants
from garment_programs.weon_shirt import Shirt, FittedShirt
from garment_programs.weon_circle_skirt import SkirtCircle, AsymmSkirtCircle
from garment_programs.weon_bands import StraightWB, FittedWB
from garment_programs.garment_enums import InterfaceName, EdgeLabel, PanelLabel
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.shirt_design import ShirtDesign
from pattern_definitions.skirt_design import SkirtDesign
from pattern_definitions.waistband_design import WaistbandDesign
from pattern_definitions.pants_design import PantsDesign
from config import AttachmentConstraint




class GarmentFactory:
    """Factory for creating garment instances.
    
    This factory encapsulates the logic for creating different types of garments
    based on design parameters. It uses the new class-based parameter definitions
    (BodyDefinition, PantsDesign, etc.) instead of raw dictionaries.
    
    Attributes:
    -----------
    _body : BodyDefinition
        The body measurements object (private, set during creation).
    _design : dict
        The full design parameters dictionary (private, set during creation).
    """
    
    def __init__(self, body: BodyDefinition, design: dict) -> None:
        """Initialize the garment factory.
        
        Parameters:
        -----------
        body : BodyDefinition
            Body measurements object containing all body parameters.
        design : dict
            Full design parameters dictionary containing all garment specifications.
        """
        self._body = body
        self._design = design
    
    @property
    def body(self) -> BodyDefinition:
        """Get the body measurements object."""
        return self._body
    
    @property
    def design(self) -> dict:
        """Get the full design parameters dictionary."""
        return self._design
    
    def create_pants(self) -> Pants:
        """Create a pants garment instance.
        
        Creates a Pants garment using the factory's body and design parameters.
        The design dictionary is automatically converted to PantsDesign internally
        by the Pants class.
        
        Returns:
        --------
        Pants
            A fully initialized Pants garment instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain pants parameters.
        """
        # Validate that pants design exists
        if 'pants' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'pants' key for pants creation"
            )
        
        pants = Pants(design=PantsDesign(self._design))
        logger.info("Creating perfect fit for loose pants and straight legs design")
        pants.apply_body_alignment(self._body)
        
        return pants
    
    def create_shirt(self, fitted: bool = False) -> Shirt:
        """Create a shirt garment instance.
        
        Parameters:
        -----------
        fitted : bool, optional
            If True, creates a fitted shirt; otherwise, a looser fit.
            Default is False.
        
        Returns:
        --------
        Shirt
            A fully initialized Shirt garment instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain shirt parameters.
        """
        if 'shirt' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'shirt' key for shirt creation"
            )
        
        shirt = Shirt(shirt_design=ShirtDesign(self._design), arm_pose_angle=self._body.arm_pose_angle, fitted=fitted)
        shirt.apply_body_alignment(self._body)

        return shirt
    
    def create_fitted_shirt(self) -> FittedShirt:
        """Create a fitted shirt garment instance.
        
        Returns:
        --------
        FittedShirt
            A fully initialized FittedShirt garment instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain shirt parameters.
        """
        if 'shirt' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'shirt' key for fitted shirt creation"
            )
        
        shirt = FittedShirt(
            shirt_design=ShirtDesign(self._design),
            arm_pose_angle=self._body.arm_pose_angle
        )
        shirt.apply_body_alignment(self._body)
        
        return shirt
    
    def create_skirt_circle(self, **kwargs) -> SkirtCircle:
        """Create a circle skirt garment instance.
        
        Parameters:
        -----------
        **kwargs
            Additional keyword arguments passed to SkirtCircle constructor
            (e.g., tag, length, slit, asymm, min_len).
        
        Returns:
        --------
        SkirtCircle
            A fully initialized SkirtCircle garment instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain skirt parameters.
        """
        if 'flare-skirt' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'flare-skirt' key for skirt creation"
            )
        
        skirt_design = SkirtDesign(self._design)
        waist_front = self._body.waist - self._body.waist_back_width
        waist_back = self._body.waist_back_width
        
        skirt = SkirtCircle(
            skirt_design=skirt_design,
            waist_front=waist_front,
            waist_back=waist_back,
            **kwargs
        )
        skirt.apply_body_alignment(self._body)
        
        return skirt
    
    def create_asymm_skirt_circle(self, **kwargs) -> AsymmSkirtCircle:
        """Create an asymmetric circle skirt garment instance.
        
        Parameters:
        -----------
        **kwargs
            Additional keyword arguments passed to AsymmSkirtCircle constructor
            (e.g., tag, length, slit).
        
        Returns:
        --------
        AsymmSkirtCircle
            A fully initialized AsymmSkirtCircle garment instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain skirt parameters.
        """
        if 'flare-skirt' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'flare-skirt' key for asymmetric skirt creation"
            )
        
        skirt_design = SkirtDesign(self._design)
        waist_front = self._body.waist - self._body.waist_back_width
        waist_back = self._body.waist_back_width
        
        skirt = AsymmSkirtCircle(
            skirt_design=skirt_design,
            waist_front=waist_front,
            waist_back=waist_back,
            **kwargs
        )
        skirt.apply_body_alignment(self._body)
        
        return skirt
    
    def create_straight_wb(
        self,
        waist: Union[float, None] = None,
        waist_back: Union[float, None] = None,
        rise: float = 1.0
    ) -> StraightWB:
        """Create a straight waistband instance.
        
        Parameters:
        -----------
        waist : float, optional
            Total waist measurement. If None, will be calculated from body.
        waist_back : float, optional
            Back waist width. If None, will be calculated from body.
        rise : float, optional
            The rise value of the bottoms that the WB is attached to.
            Default is 1.0.
        
        Returns:
        --------
        StraightWB
            A fully initialized StraightWB instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain waistband parameters.
        """
        if 'waistband' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'waistband' key for waistband creation"
            )
        
        waistband_design = WaistbandDesign(self._design)
        
        # Use provided values or calculate from body
        if waist is None:
            waist = self._body.waist
        if waist_back is None:
            waist_back = self._body.waist_back_width
        waist_front = waist - waist_back
        
        wb = StraightWB(
            waistband_design=waistband_design,
            waist=waist,
            waist_back=waist_back,
            waist_front=waist_front,
            rise=rise
        )
        wb.apply_body_alignment(self._body)
        
        return wb
    
    def create_fitted_wb(self, rise: float = 1.0) -> FittedWB:
        """Create a fitted waistband (yoke) instance.
        
        Parameters:
        -----------
        rise : float, optional
            The rise value of the bottoms that the WB is attached to.
            Default is 1.0.
        
        Returns:
        --------
        FittedWB
            A fully initialized FittedWB instance.
        
        Raises:
        -------
        ValueError
            If the design dictionary does not contain waistband parameters.
        """
        if 'waistband' not in self._design:
            raise ValueError(
                "Design dictionary must contain 'waistband' key for fitted waistband creation"
            )
        
        waistband_design = WaistbandDesign(self._design)
        
        waist = self._body.waist
        waist_back = self._body.waist_back_width
        waist_front = waist - waist_back
        hips = self._body.hips
        hips_back = self._body.hip_back_width
        
        wb = FittedWB(
            waistband_design=waistband_design,
            waist=waist,
            waist_back=waist_back,
            waist_front=waist_front,
            hips=hips,
            hips_back=hips_back,
            rise=rise
        )
        wb.apply_body_alignment(self._body)
        
        return wb
    
    def create_composite_garment(self) -> pyg.Component:
        """Create a composite garment (dress/jumpsuit) with upper, waistband, and lower components.
        
        This method creates a composite garment similar to MetaGarment, combining:
        - Upper garment (if meta.upper.v is specified)
        - Waistband (if meta.wb.v is specified and lower garment exists)
        - Lower garment (if meta.bottom.v is specified)
        
        The components are connected in order: upper -> waistband -> lower
        
        Returns:
        --------
        pyg.Component
            A composite garment component containing the upper, waistband (if any),
            and lower garments connected together.
        
        Raises:
        -------
        ValueError
            If neither upper nor lower garment is specified, or if required
            design parameters are missing.
        """
        
        # Get garment types from design
        upper_type = self._design.get('meta', {}).get('upper', {}).get('v')
        lower_type = self._design.get('meta', {}).get('bottom', {}).get('v')
        wb_type = self._design.get('meta', {}).get('wb', {}).get('v')
        
        # Validate that at least one garment type is specified
        if not upper_type and not lower_type:
            raise ValueError(
                "Composite garment must specify either 'meta.upper.v' or 'meta.bottom.v'"
            )
        
        # Create composite component
        composite = pyg.Component('CompositeGarment')
        composite.subs = []
        composite.stitching_rules = pyg.Stitches()
        
        # Create upper garment if specified
        if upper_type:
            if upper_type == 'Shirt':
                upper = self.create_shirt(fitted=False)
            elif upper_type == 'FittedShirt':
                upper = self.create_fitted_shirt()
            else:
                raise ValueError(f"Unsupported upper garment type: {upper_type}")
            
            composite.subs.append(upper)
            upper.set_panel_label(PanelLabel.BODY, overwrite=False)
        
        # Create lower garment if specified
        lower: pyg.Component | None = None
        if lower_type:
            if lower_type == 'Pants':
                lower = self.create_pants()
            elif lower_type == 'SkirtCircle':
                lower = self.create_skirt_circle()
            elif lower_type == 'AsymmSkirtCircle':
                lower = self.create_asymm_skirt_circle()
            else:
                raise ValueError(f"Unsupported lower garment type: {lower_type}")
        
        # Create waistband if specified and lower garment exists
        if wb_type and lower:
            # Get waist width from lower garment
            if hasattr(lower, 'get_waist_width'):
                # For skirts (SkirtCircle, AsymmSkirtCircle)
                waist_width = lower.get_waist_width()
            elif hasattr(lower, 'right') and hasattr(lower.right, 'pants_design'):
                # For pants, access via right.pants_design
                waist_width = lower.right.pants_design.waist
            else:
                # Fallback: use body waist measurement
                waist_width = self._body.waist
            
            if wb_type == 'StraightWB':
                wb = self.create_straight_wb(
                    waist=waist_width,
                    waist_back=self._body.waist_back_width,
                    rise=1.0
                )
            elif wb_type == 'FittedWB':
                wb = self.create_fitted_wb(rise=1.0)
            else:
                raise ValueError(f"Unsupported waistband type: {wb_type}")
            
            composite.subs.append(wb)
            
            # Place waistband below upper garment (if upper exists)
            if composite.subs and len(composite.subs) > 1:
                wb.place_by_interface(
                    wb.interfaces[InterfaceName.TOP],
                    composite.subs[-2].interfaces[InterfaceName.BOTTOM],
                    gap=5
                )
                composite.stitching_rules.append((
                    composite.subs[-2].interfaces[InterfaceName.BOTTOM],
                    wb.interfaces[InterfaceName.TOP]
                ))
            
            # Add waist label
            wb.interfaces[InterfaceName.TOP].edges.propagate_label(EdgeLabel.LOWER_INTERFACE)
            wb.set_panel_label(PanelLabel.BODY, overwrite=False)
        
        # Attach lower garment if present
        if lower:
            composite.subs.append(lower)
            
            # Place lower garment below upper or waistband
            if len(composite.subs) > 1:
                lower.place_by_interface(
                    lower.interfaces[InterfaceName.TOP],
                    composite.subs[-2].interfaces[InterfaceName.BOTTOM],
                    gap=5
                )
                composite.stitching_rules.append((
                    composite.subs[-2].interfaces[InterfaceName.BOTTOM],
                    lower.interfaces[InterfaceName.TOP]
                ))
            
            # Add waist label if no waistband
            if not wb_type:
                lower.interfaces[InterfaceName.TOP].edges.propagate_label(EdgeLabel.LOWER_INTERFACE)
            
            # Set panel segmentation labels
            lower.set_panel_label(PanelLabel.LEG, overwrite=False)
        
        return composite
    
    @staticmethod
    def create_pants_from_params(
        body: BodyDefinition,
        design: dict
    ) -> Pants:
        """Static factory method to create pants directly.
        
        Convenience method for creating pants without instantiating the factory.
        
        Parameters:
        -----------
        body : BodyDefinition
            Body measurements object containing all body parameters.
        design : dict
            Design parameters dictionary containing pants specifications.
        
        Returns:
        --------
        Pants
            A fully initialized Pants garment instance.
        """
        factory = GarmentFactory(body, design)
        return factory.create_pants()


def create_garment(
    garment_type: str,
    body: BodyDefinition,
    design: dict,
    **kwargs: Any
) -> tuple[pyg.Component, list[AttachmentConstraint]]:
    """Factory function to create garments by type name.
    
    This function provides a simple interface for creating garments based on
    their type name, similar to the original MetaGarment approach but using
    the factory pattern.
    
    Parameters:
    -----------
    garment_type : str
        Type of garment to create. Supported types:
        - 'Pants': Creates a pants garment
        - 'Shirt': Creates a shirt garment (use fitted=False in kwargs for loose fit)
        - 'FittedShirt': Creates a fitted shirt garment
        - 'SkirtCircle': Creates a circle skirt
        - 'AsymmSkirtCircle': Creates an asymmetric circle skirt
        - 'StraightWB': Creates a straight waistband
        - 'FittedWB': Creates a fitted waistband (yoke)
    body : BodyDefinition
        Body measurements object containing all body parameters.
    design : dict
        Design parameters dictionary containing garment specifications.
    **kwargs
        Additional keyword arguments passed to the garment constructor.
        For example:
        - For Shirt: fitted=True/False
        - For SkirtCircle/AsymmSkirtCircle: tag, length, slit, etc.
        - For StraightWB: waist, waist_back, rise
        - For FittedWB: rise
    
    Returns:
    --------
    tuple[pyg.Component, list[AttachmentConstraint]]
        A tuple containing:
        - The created garment instance (Pants, Shirt, FittedShirt, SkirtCircle,
          AsymmSkirtCircle, StraightWB, or FittedWB)
        - A list of AttachmentConstraint objects for the garment.
          For pants, this includes a crotch constraint. For other garment types,
          this is an empty list.
    
    Raises:
    -------
    ValueError
        If the garment_type is not recognized or if required design parameters
        are missing.
    """
    factory = GarmentFactory(body, design)
    
    garment_creators = {
        'Pants': factory.create_pants,
        'Shirt': lambda: factory.create_shirt(fitted=kwargs.get('fitted', False)),
        'FittedShirt': factory.create_fitted_shirt,
        'SkirtCircle': lambda: factory.create_skirt_circle(**{k: v for k, v in kwargs.items() if k not in ['fitted']}),
        'AsymmSkirtCircle': lambda: factory.create_asymm_skirt_circle(**{k: v for k, v in kwargs.items() if k not in ['fitted']}),
        'StraightWB': lambda: factory.create_straight_wb(
            waist=kwargs.get('waist'),
            waist_back=kwargs.get('waist_back'),
            rise=kwargs.get('rise', 1.0)
        ),
        'FittedWB': lambda: factory.create_fitted_wb(rise=kwargs.get('rise', 1.0)),
    }
    
    if garment_type not in garment_creators:
        raise ValueError(
            f"Unknown garment type: {garment_type}. "
            f"Supported types: {list(garment_creators.keys())}"
        )
    
    garment = garment_creators[garment_type]()
    
    # Get attachment constraints from the garment itself
    # All garment classes implement get_attachment_constraints() method
    constraints = garment.get_attachment_constraints()  # type: ignore[attr-defined]
    
    return garment, constraints

