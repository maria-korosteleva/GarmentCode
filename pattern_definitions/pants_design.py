"""Pants design parameter class definition.

This module defines the PantsDesign class that encapsulates all design parameters
for pants garments, replacing the previous dictionary-based approach.
"""

from typing import Optional


class CuffDesign:
    """Design parameters for pants cuff.
    
    Attributes:
    -----------
    type : Optional[str]
        Type of cuff (e.g., 'straight', 'tapered', None for no cuff).
    top_ruffle : float
        Ruffle factor at the top of the cuff.
    cuff_len : float
        Length of the cuff.
    skirt_fraction : float
        Fraction for skirt-style cuffs.
    skirt_flare : float
        Flare factor for skirt-style cuffs.
    skirt_ruffle : float
        Ruffle factor for skirt-style cuffs.
    """
    
    def __init__(self, cuff_dict: dict) -> None:
        """Initialize cuff design from dictionary.
        
        Parameters:
        -----------
        cuff_dict : dict
            Dictionary containing cuff parameters with 'v' keys.
        """
        self._type: Optional[str] = cuff_dict.get('type', {}).get('v')
        self._top_ruffle: float = cuff_dict.get('top_ruffle', {}).get('v', 1.0)
        self._cuff_len: float = cuff_dict.get('cuff_len', {}).get('v', 0.1)
        self._skirt_fraction: float = cuff_dict.get('skirt_fraction', {}).get('v', 0.5)
        self._skirt_flare: float = cuff_dict.get('skirt_flare', {}).get('v', 1.2)
        self._skirt_ruffle: float = cuff_dict.get('skirt_ruffle', {}).get('v', 1.0)
    
    @property
    def type(self) -> Optional[str]:
        """Type of cuff (e.g., 'straight', 'tapered', None for no cuff)."""
        return self._type
    
    @property
    def top_ruffle(self) -> float:
        """Ruffle factor at the top of the cuff."""
        return self._top_ruffle
    
    @property
    def cuff_len(self) -> float:
        """Length of the cuff."""
        return self._cuff_len
    
    @property
    def skirt_fraction(self) -> float:
        """Fraction for skirt-style cuffs."""
        return self._skirt_fraction
    
    @property
    def skirt_flare(self) -> float:
        """Flare factor for skirt-style cuffs."""
        return self._skirt_flare
    
    @property
    def skirt_ruffle(self) -> float:
        """Ruffle factor for skirt-style cuffs."""
        return self._skirt_ruffle


class PantsDesign:
    """Design parameters for pants garment.
    
    This class encapsulates all design parameters needed to construct pants panels,
    replacing the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    front_rise : float
        Front rise measurement from crotch to waist.
    back_rise : float
        Back rise measurement from crotch to waist.
    length_waist_to_hip : float
        Vertical distance from waist to hip line.
    length_1 : float
        First length segment for panel construction.
    length_2 : float
        Second length segment for panel construction.
    length_3 : float
        Third length segment for panel construction.
    waist : float
        Waist measurement (full circumference).
    width_1 : float
        First width measurement for panel construction.
    width_2 : float
        Second width measurement for panel construction.
    width_3 : float
        Third width measurement for panel construction.
    width_4 : float
        Fourth width measurement for panel construction.
    width_hips : float
        Hip width measurement (full circumference).
    width_gusset_crotch : float
        Width of gusset at crotch.
    width_gusset_crotch_back: float | None
        Width of gusset at crotch on the back panel. If given, width_gusset_crotch is used for the front panel.
    crotch_shift_ratio : float
        Ratio for shifting crotch position.
    cuff : CuffDesign
        Cuff design parameters.
    """
    
    def __init__(self, pants_dict: dict) -> None:
        """Initialize pants design from dictionary.
        
        Parameters:
        -----------
        pants_dict : dict
            Dictionary containing pants design parameters. Can be either:
            - The full design dict (will extract 'pants' key)
            - The 'pants' sub-dictionary directly
            
            Each parameter should have a 'v' key containing the actual value.
        """
        # Handle both full design dict and pants sub-dict
        if 'pants' in pants_dict:
            pants_dict = pants_dict['pants']
        
        # Extract all parameters with safe defaults (stored as private attributes)
        self._front_rise: float = pants_dict.get('front_rise', {}).get('v', 30.0)
        self._back_rise: float = pants_dict.get('back_rise', {}).get('v', 39.0)
        self._length_waist_to_hip: float = pants_dict.get('length_waist_to_hip', {}).get('v', 27.0)
        self._length_thigh_to_knee: float = pants_dict.get('length_1', {}).get('v', 35.0)
        self._length_knee_to_calf: float = pants_dict.get('length_2', {}).get('v', 20.0)
        self._length_calf_to_ankle: float = pants_dict.get('length_3', {}).get('v', 20.0)
        self._waist: float = pants_dict.get('waist', {}).get('v', 38.0)
        self._width_thigh: float = pants_dict.get('width_1', {}).get('v', 26.5)
        self._width_knee: float = pants_dict.get('width_2', {}).get('v', 17.5)
        self._width_calf: float = pants_dict.get('width_3', {}).get('v', 16.1)
        self._width_ankle: float = pants_dict.get('width_4', {}).get('v', 12.1)
        self._width_hips: float = pants_dict.get('width_hips', {}).get('v', 49.0)
        self._width_gusset_crotch: float = pants_dict.get('width_gusset_crotch', {}).get('v', 7.0)
        self._width_gusset_crotch_back: float | None = pants_dict.get('width_gusset_crotch_back', {}).get('v', None)
        self._crotch_shift_ratio: float = pants_dict.get('crotch_shift_ratio', {}).get('v', 0.5)
        
        # Initialize nested cuff design
        cuff_dict = pants_dict.get('cuff', {})
        self._cuff: CuffDesign = CuffDesign(cuff_dict)
    
    @property
    def front_rise(self) -> float:
        """Front rise measurement from crotch to waist."""
        return self._front_rise
    
    @property
    def back_rise(self) -> float:
        """Back rise measurement from crotch to waist."""
        return self._back_rise
    
    @property
    def length_waist_to_hip(self) -> float:
        """Vertical distance from waist to hip line."""
        return self._length_waist_to_hip
    
    @property
    def length_thigh_to_knee(self) -> float:
        """Length segment from thigh to knee."""
        return self._length_thigh_to_knee
    
    @property
    def length_knee_to_calf(self) -> float:
        """Length segment from knee to calf."""
        return self._length_knee_to_calf
    
    @property
    def length_calf_to_ankle(self) -> float:
        """Length segment from calf to ankle."""
        return self._length_calf_to_ankle
    
    @property
    def waist(self) -> float:
        """Waist measurement (full circumference)."""
        return self._waist
    
    @property
    def width_thigh(self) -> float:
        """Width measurement at thigh level."""
        return self._width_thigh
    
    @property
    def width_knee(self) -> float:
        """Width measurement at knee level."""
        return self._width_knee
    
    @property
    def width_calf(self) -> float:
        """Width measurement at calf level."""
        return self._width_calf
    
    @property
    def width_ankle(self) -> float:
        """Width measurement at ankle level."""
        return self._width_ankle
    
    @property
    def width_hips(self) -> float:
        """Hip width measurement (full circumference)."""
        return self._width_hips
    
    @property
    def width_gusset_crotch(self) -> float:
        """Width of gusset at crotch."""
        return self._width_gusset_crotch
    
    @property
    def width_gusset_crotch_back(self) -> float | None:
        """Width of gusset at crotch on the back panel."""
        return self._width_gusset_crotch_back
    
    @property
    def crotch_shift_ratio(self) -> float:
        """Ratio for shifting crotch position."""
        return self._crotch_shift_ratio
    
    @property
    def cuff(self) -> CuffDesign:
        """Cuff design parameters."""
        return self._cuff

