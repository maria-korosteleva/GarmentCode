"""Skirt design parameter class definition.

This module defines the SkirtDesign class that encapsulates all design parameters
for circle skirt garments, replacing the previous dictionary-based approach.
"""


class SkirtCutDesign:
    """Design parameters for skirt cut/slit.
    
    Attributes:
    -----------
    add : bool
        Whether to add a cut to the skirt.
    depth : float
        Depth of the cut.
    width : float
        Width of the cut.
    place : float
        Placement position of the cut (-1 to 1, where 0 is center).
    """
    
    def __init__(self, cut_dict: dict) -> None:
        """Initialize skirt cut design from dictionary.
        
        Parameters:
        -----------
        cut_dict : dict
            Dictionary containing cut parameters with 'v' keys.
        """
        self._add: bool = cut_dict.get('add', {}).get('v', False)
        self._depth: float = cut_dict.get('depth', {}).get('v', 0.5)
        self._width: float = cut_dict.get('width', {}).get('v', 0.1)
        self._place: float = cut_dict.get('place', {}).get('v', -0.5)
    
    @property
    def add(self) -> bool:
        """Whether to add a cut to the skirt."""
        return self._add
    
    @property
    def depth(self) -> float:
        """Depth of the cut."""
        return self._depth
    
    @property
    def width(self) -> float:
        """Width of the cut."""
        return self._width
    
    @property
    def place(self) -> float:
        """Placement position of the cut (-1 to 1, where 0 is center)."""
        return self._place


class SkirtAsymmDesign:
    """Design parameters for asymmetric skirt.
    
    Attributes:
    -----------
    front_length : float
        Front length multiplier for asymmetric skirts.
    """
    
    def __init__(self, asymm_dict: dict) -> None:
        """Initialize asymmetric skirt design from dictionary.
        
        Parameters:
        -----------
        asymm_dict : dict
            Dictionary containing asymmetric parameters with 'v' keys.
        """
        self._front_length: float = asymm_dict.get('front_length', {}).get('v', 0.5)
    
    @property
    def front_length(self) -> float:
        """Front length multiplier for asymmetric skirts."""
        return self._front_length


class SkirtDesign:
    """Design parameters for circle skirt garment.
    
    This class encapsulates all design parameters needed to construct circle skirt panels,
    replacing the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    length : float
        Length of the skirt.
    waist_width : float
        Waist width measurement (full circumference).
    bottom_width : float
        Bottom width measurement (full circumference).
    asymm : SkirtAsymmDesign
        Asymmetric design parameters (if applicable).
    cut : SkirtCutDesign
        Cut/slit design parameters.
    """
    
    def __init__(self, design_dict: dict) -> None:
        """Initialize skirt design from dictionary.
        
        Parameters:
        -----------
        design_dict : dict
            Dictionary containing skirt design parameters. Can be either:
            - The full design dict (will extract 'flare-skirt' key)
            - The 'flare-skirt' sub-dictionary directly
            
            Each parameter should have a 'v' key containing the actual value.
        """
        # Handle both full design dict and flare-skirt sub-dict
        if 'flare-skirt' in design_dict:
            skirt_dict = design_dict['flare-skirt']
        else:
            skirt_dict = design_dict
        
        # Extract all parameters with safe defaults (stored as private attributes)
        self._length: float = skirt_dict.get('length', {}).get('v', 80.0)
        self._waist_width: float = skirt_dict.get('waist_width', {}).get('v', 48.0)
        self._bottom_width: float = skirt_dict.get('bottom_width', {}).get('v', 90.0)
        
        # Initialize nested designs
        asymm_dict = skirt_dict.get('asymm', {})
        self._asymm: SkirtAsymmDesign = SkirtAsymmDesign(asymm_dict)
        
        cut_dict = skirt_dict.get('cut', {})
        self._cut: SkirtCutDesign = SkirtCutDesign(cut_dict)
    
    @property
    def length(self) -> float:
        """Length of the skirt."""
        return self._length
    
    @property
    def waist_width(self) -> float:
        """Waist width measurement (full circumference)."""
        return self._waist_width
    
    @property
    def bottom_width(self) -> float:
        """Bottom width measurement (full circumference)."""
        return self._bottom_width
    
    @property
    def asymm(self) -> SkirtAsymmDesign:
        """Asymmetric design parameters (if applicable)."""
        return self._asymm
    
    @property
    def cut(self) -> SkirtCutDesign:
        """Cut/slit design parameters."""
        return self._cut

