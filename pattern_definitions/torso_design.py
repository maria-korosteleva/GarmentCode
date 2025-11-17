"""Torso design parameter class definition.

This module defines the TorsoDesign class that encapsulates all design parameters
for torso (T-shirt style) garments, replacing the previous dictionary-based approach.
"""


class TorsoDesign:
    """Design parameters for torso garment (simple non-fitted upper garment).
    
    This class encapsulates all design parameters needed to construct torso panels,
    replacing the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    smallest_width : float
        Smallest width measurement.
    width_chest : float
        Width at chest level.
    width_waist : float
        Width at waist level.
    width_hip : float
        Width at hip level.
    neck_to_shoulder_distance : float
        Distance from neck to shoulder.
    neck_width : float
        Width of the neck opening.
    shoulder_slant : float
        Shoulder slant angle.
    waist_over_bust_line_height : float
        Height from waist over bust line.
    back_width : float
        Back width measurement.
    front_length : float
        Front panel length.
    back_length : float
        Back panel length.
    scye_depth : float
        Scye (armhole) depth.
    strapless : bool
        Whether the garment is strapless.
    length : float
        Length multiplier for the shirt.
    width : float
        Width multiplier for the shirt.
    flare : float
        Flare factor for the shirt.
    """
    
    def __init__(self, design_dict: dict) -> None:
        """Initialize torso design from dictionary.
        
        Parameters:
        -----------
        design_dict : dict
            Dictionary containing torso design parameters. Can be either:
            - The full design dict (will extract 'shirt' key)
            - The 'shirt' sub-dictionary directly
            
            Each parameter should have a 'v' key containing the actual value.
        """
        # Handle both full design dict and shirt sub-dict
        if 'shirt' in design_dict:
            shirt_dict = design_dict['shirt']
        else:
            shirt_dict = design_dict
        
        # Extract all parameters with safe defaults (stored as private attributes)
        self._smallest_width: float = shirt_dict.get('smallest_width', {}).get('v', 32.0)
        self._width_chest: float = shirt_dict.get('width_chest', {}).get('v', 44.0)
        self._width_waist: float = shirt_dict.get('width_waist', {}).get('v', 40.0)
        self._width_hip: float = shirt_dict.get('width_hip', {}).get('v', 45.0)
        self._neck_to_shoulder_distance: float = shirt_dict.get('neck_to_shoulder_distance', {}).get('v', 10.2)
        self._neck_width: float = shirt_dict.get('neck_width', {}).get('v', 16.0)
        self._shoulder_slant: float = shirt_dict.get('shoulder_slant', {}).get('v', 3.5)
        self._waist_over_bust_line_height: float = shirt_dict.get('waist_over_bust_line_height', {}).get('v', 41.7)
        self._back_width: float = shirt_dict.get('back_width', {}).get('v', 33.5)
        self._front_length: float = shirt_dict.get('front_length', {}).get('v', 63.0)
        self._back_length: float = shirt_dict.get('back_length', {}).get('v', 69.0)
        self._scye_depth: float = shirt_dict.get('scye_depth', {}).get('v', 21.7)
        self._strapless: bool = shirt_dict.get('strapless', {}).get('v', False)
        self._length: float = shirt_dict.get('length', {}).get('v', 1.2)
        self._width: float = shirt_dict.get('width', {}).get('v', 1.05)
        self._flare: float = shirt_dict.get('flare', {}).get('v', 1.0)
    
    @property
    def smallest_width(self) -> float:
        """Smallest width measurement."""
        return self._smallest_width
    
    @property
    def width_chest(self) -> float:
        """Width at chest level."""
        return self._width_chest
    
    @property
    def width_waist(self) -> float:
        """Width at waist level."""
        return self._width_waist
    
    @property
    def width_hip(self) -> float:
        """Width at hip level."""
        return self._width_hip
    
    @property
    def neck_to_shoulder_distance(self) -> float:
        """Distance from neck to shoulder."""
        return self._neck_to_shoulder_distance
    
    @property
    def neck_width(self) -> float:
        """Width of the neck opening."""
        return self._neck_width
    
    @property
    def shoulder_slant(self) -> float:
        """Shoulder slant angle."""
        return self._shoulder_slant
    
    @property
    def waist_over_bust_line_height(self) -> float:
        """Height from waist over bust line."""
        return self._waist_over_bust_line_height
    
    @property
    def back_width(self) -> float:
        """Back width measurement."""
        return self._back_width
    
    @property
    def front_length(self) -> float:
        """Front panel length."""
        return self._front_length
    
    @property
    def back_length(self) -> float:
        """Back panel length."""
        return self._back_length
    
    @property
    def scye_depth(self) -> float:
        """Scye (armhole) depth."""
        return self._scye_depth
    
    @property
    def strapless(self) -> bool:
        """Whether the garment is strapless."""
        return self._strapless
    
    @property
    def length(self) -> float:
        """Length multiplier for the shirt."""
        return self._length
    
    @property
    def width(self) -> float:
        """Width multiplier for the shirt."""
        return self._width
    
    @property
    def flare(self) -> float:
        """Flare factor for the shirt."""
        return self._flare

