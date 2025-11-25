"""Waistband design parameter class definition.

This module defines the WaistbandDesign class that encapsulates all design parameters
for waistband garments, replacing the previous dictionary-based approach.
"""


class WaistbandDesign:
    """Design parameters for waistband garment.
    
    This class encapsulates all design parameters needed to construct waistband panels,
    replacing the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    width : float
        Width of the waistband.
    """
    
    def __init__(self, design_dict: dict) -> None:
        """Initialize waistband design from dictionary.
        
        Parameters:
        -----------
        design_dict : dict
            Dictionary containing waistband design parameters. Can be either:
            - The full design dict (will extract 'waistband' key)
            - The 'waistband' sub-dictionary directly
            
            Each parameter should have a 'v' key containing the actual value.
        """
        # Handle both full design dict and waistband sub-dict
        if 'waistband' in design_dict:
            waistband_dict = design_dict['waistband']
        else:
            waistband_dict = design_dict
        
        # Extract all parameters with safe defaults (stored as private attributes)
        self._width: float = waistband_dict.get('width', {}).get('v', 1.0)
    
    @property
    def width(self) -> float:
        """Width of the waistband."""
        return self._width

