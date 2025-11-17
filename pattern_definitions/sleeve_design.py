"""Sleeve design parameter class definition.

This module defines the SleeveDesign class that encapsulates all design parameters
for sleeve garments, replacing the previous dictionary-based approach.
"""

from pattern_definitions.pants_design import CuffDesign


class SleeveDesign:
    """Design parameters for sleeve garment.
    
    This class encapsulates all design parameters needed to construct sleeve panels,
    replacing the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    sleeveless : bool
        Whether the sleeve is sleeveless.
    armhole_shape : str
        Shape of the armhole (e.g., 'ArmholeCurve', 'ArmholeSquare', 'ArmholeAngle').
    length : float
        Length of the sleeve.
    bicep_width : float
        Width at the bicep level.
    elbow_width : float
        Width at the elbow level.
    connecting_width : float
        Width at the connecting point (armhole).
    end_width : float
        Width at the end of the sleeve (wrist).
    sleeve_angle : int
        Angle of the sleeve in degrees.
    opening_dir_mix : float
        Opening direction mix factor.
    standing_shoulder : bool
        Whether to use standing shoulder.
    standing_shoulder_len : float
        Length of standing shoulder extension.
    connect_ruffle : float
        Ruffle factor at the connection point.
    smoothing_coeff : float
        Smoothing coefficient for curves.
    cuff : CuffDesign
        Cuff design parameters (reusing from waistband design).
    """
    
    def __init__(self, design_dict: dict) -> None:
        """Initialize sleeve design from dictionary.
        
        Parameters:
        -----------
        design_dict : dict
            Dictionary containing sleeve design parameters. Can be either:
            - The full design dict (will extract 'sleeve' key)
            - The 'sleeve' sub-dictionary directly
            
            Each parameter should have a 'v' key containing the actual value.
        """
        # Handle both full design dict and sleeve sub-dict
        if 'sleeve' in design_dict:
            sleeve_dict = design_dict['sleeve']
        else:
            sleeve_dict = design_dict
        
        # Extract all parameters with safe defaults (stored as private attributes)
        self._sleeveless: bool = sleeve_dict.get('sleeveless', {}).get('v', False)
        self._armhole_shape: str = sleeve_dict.get('armhole_shape', {}).get('v', 'ArmholeCurve')
        self._length: float = sleeve_dict.get('length', {}).get('v', 63.0)
        self._bicep_width: float = sleeve_dict.get('bicep_width', {}).get('v', 17.5)
        self._elbow_width: float = sleeve_dict.get('elbow_width', {}).get('v', 13.6)
        self._connecting_width: float = sleeve_dict.get('connecting_width', {}).get('v', 0.1)
        self._end_width: float = sleeve_dict.get('end_width', {}).get('v', 9.0)
        self._sleeve_angle: int = sleeve_dict.get('sleeve_angle', {}).get('v', 10)
        self._opening_dir_mix: float = sleeve_dict.get('opening_dir_mix', {}).get('v', 0.1)
        self._standing_shoulder: bool = sleeve_dict.get('standing_shoulder', {}).get('v', False)
        self._standing_shoulder_len: float = sleeve_dict.get('standing_shoulder_len', {}).get('v', 5.0)
        self._connect_ruffle: float = sleeve_dict.get('connect_ruffle', {}).get('v', 1.0)
        self._smoothing_coeff: float = sleeve_dict.get('smoothing_coeff', {}).get('v', 0.25)
        
        # Initialize nested cuff design
        cuff_dict = sleeve_dict.get('cuff', {})
        self._cuff: CuffDesign = CuffDesign(cuff_dict)
    
    @property
    def sleeveless(self) -> bool:
        """Whether the sleeve is sleeveless."""
        return self._sleeveless
    
    @property
    def armhole_shape(self) -> str:
        """Shape of the armhole (e.g., 'ArmholeCurve', 'ArmholeSquare', 'ArmholeAngle')."""
        return self._armhole_shape
    
    @property
    def length(self) -> float:
        """Length of the sleeve."""
        return self._length
    
    @property
    def bicep_width(self) -> float:
        """Width at the bicep level."""
        return self._bicep_width
    
    @property
    def elbow_width(self) -> float:
        """Width at the elbow level."""
        return self._elbow_width
    
    @property
    def connecting_width(self) -> float:
        """Width at the connecting point (armhole)."""
        return self._connecting_width
    
    @property
    def end_width(self) -> float:
        """Width at the end of the sleeve (wrist)."""
        return self._end_width
    
    @property
    def sleeve_angle(self) -> int:
        """Angle of the sleeve in degrees."""
        return self._sleeve_angle
    
    @property
    def opening_dir_mix(self) -> float:
        """Opening direction mix factor."""
        return self._opening_dir_mix
    
    @property
    def standing_shoulder(self) -> bool:
        """Whether to use standing shoulder."""
        return self._standing_shoulder
    
    @property
    def standing_shoulder_len(self) -> float:
        """Length of standing shoulder extension."""
        return self._standing_shoulder_len
    
    @property
    def connect_ruffle(self) -> float:
        """Ruffle factor at the connection point."""
        return self._connect_ruffle
    
    @property
    def smoothing_coeff(self) -> float:
        """Smoothing coefficient for curves."""
        return self._smoothing_coeff
    
    @property
    def cuff(self) -> CuffDesign:
        """Cuff design parameters."""
        return self._cuff

