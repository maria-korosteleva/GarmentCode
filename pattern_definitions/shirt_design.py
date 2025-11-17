"""Shirt design parameter class definition.

This module defines the ShirtDesign class that encapsulates all design parameters
for shirt garments, replacing the previous dictionary-based approach.
"""

from typing import Optional

from pattern_definitions.sleeve_design import SleeveDesign
from pattern_definitions.torso_design import TorsoDesign


class CollarComponentDesign:
    """Design parameters for collar component.
    
    Attributes:
    -----------
    style : Optional[str]
        Style of the collar component (e.g., 'SimpleLapel', None).
    depth : int
        Depth of the collar component.
    lapel_standing : bool
        Whether the lapel is standing.
    hood_depth : float
        Depth of hood (if applicable).
    hood_length : float
        Length of hood (if applicable).
    """
    
    def __init__(self, component_dict: dict) -> None:
        """Initialize collar component design from dictionary.
        
        Parameters:
        -----------
        component_dict : dict
            Dictionary containing component parameters with 'v' keys.
        """
        self._style: Optional[str] = component_dict.get('style', {}).get('v')
        self._depth: int = component_dict.get('depth', {}).get('v', 7)
        self._lapel_standing: bool = component_dict.get('lapel_standing', {}).get('v', False)
        self._hood_depth: float = component_dict.get('hood_depth', {}).get('v', 1.0)
        self._hood_length: float = component_dict.get('hood_length', {}).get('v', 1.0)
    
    @property
    def style(self) -> Optional[str]:
        """Style of the collar component (e.g., 'SimpleLapel', None)."""
        return self._style
    
    @property
    def depth(self) -> int:
        """Depth of the collar component."""
        return self._depth
    
    @property
    def lapel_standing(self) -> bool:
        """Whether the lapel is standing."""
        return self._lapel_standing
    
    @property
    def hood_depth(self) -> float:
        """Depth of hood (if applicable)."""
        return self._hood_depth
    
    @property
    def hood_length(self) -> float:
        """Length of hood (if applicable)."""
        return self._hood_length


class CollarDesign:
    """Design parameters for collar.
    
    Attributes:
    -----------
    f_collar : str
        Front collar type (e.g., 'CircleNeckHalf').
    b_collar : str
        Back collar type (e.g., 'CircleNeckHalf').
    width : float
        Width of the collar.
    fc_depth : float
        Front collar depth.
    bc_depth : float
        Back collar depth.
    fc_angle : int
        Front collar angle in degrees.
    bc_angle : int
        Back collar angle in degrees.
    f_bezier_x : float
        Front bezier X control point.
    f_bezier_y : float
        Front bezier Y control point.
    b_bezier_x : float
        Back bezier X control point.
    b_bezier_y : float
        Back bezier Y control point.
    f_flip_curve : bool
        Whether to flip front curve.
    b_flip_curve : bool
        Whether to flip back curve.
    component : CollarComponentDesign
        Collar component design parameters.
    """
    
    def __init__(self, collar_dict: dict) -> None:
        """Initialize collar design from dictionary.
        
        Parameters:
        -----------
        collar_dict : dict
            Dictionary containing collar parameters with 'v' keys.
        """
        self._f_collar: str = collar_dict.get('f_collar', {}).get('v', 'CircleNeckHalf')
        self._b_collar: str = collar_dict.get('b_collar', {}).get('v', 'CircleNeckHalf')
        self._width: float = collar_dict.get('width', {}).get('v', 16.0)
        self._fc_depth: float = collar_dict.get('fc_depth', {}).get('v', 8.5)
        self._bc_depth: float = collar_dict.get('bc_depth', {}).get('v', 2.0)
        self._fc_angle: int = collar_dict.get('fc_angle', {}).get('v', 95)
        self._bc_angle: int = collar_dict.get('bc_angle', {}).get('v', 95)
        self._f_bezier_x: float = collar_dict.get('f_bezier_x', {}).get('v', 0.3)
        self._f_bezier_y: float = collar_dict.get('f_bezier_y', {}).get('v', 0.55)
        self._b_bezier_x: float = collar_dict.get('b_bezier_x', {}).get('v', 0.15)
        self._b_bezier_y: float = collar_dict.get('b_bezier_y', {}).get('v', 0.1)
        self._f_flip_curve: bool = collar_dict.get('f_flip_curve', {}).get('v', False)
        self._b_flip_curve: bool = collar_dict.get('b_flip_curve', {}).get('v', False)
        
        # Initialize nested component design
        component_dict = collar_dict.get('component', {})
        self._component: CollarComponentDesign = CollarComponentDesign(component_dict)
    
    @property
    def f_collar(self) -> str:
        """Front collar type (e.g., 'CircleNeckHalf')."""
        return self._f_collar
    
    @property
    def b_collar(self) -> str:
        """Back collar type (e.g., 'CircleNeckHalf')."""
        return self._b_collar
    
    @property
    def width(self) -> float:
        """Width of the collar."""
        return self._width
    
    @property
    def fc_depth(self) -> float:
        """Front collar depth."""
        return self._fc_depth
    
    @property
    def bc_depth(self) -> float:
        """Back collar depth."""
        return self._bc_depth
    
    @property
    def fc_angle(self) -> int:
        """Front collar angle in degrees."""
        return self._fc_angle
    
    @property
    def bc_angle(self) -> int:
        """Back collar angle in degrees."""
        return self._bc_angle
    
    @property
    def f_bezier_x(self) -> float:
        """Front bezier X control point."""
        return self._f_bezier_x
    
    @property
    def f_bezier_y(self) -> float:
        """Front bezier Y control point."""
        return self._f_bezier_y
    
    @property
    def b_bezier_x(self) -> float:
        """Back bezier X control point."""
        return self._b_bezier_x
    
    @property
    def b_bezier_y(self) -> float:
        """Back bezier Y control point."""
        return self._b_bezier_y
    
    @property
    def f_flip_curve(self) -> bool:
        """Whether to flip front curve."""
        return self._f_flip_curve
    
    @property
    def b_flip_curve(self) -> bool:
        """Whether to flip back curve."""
        return self._b_flip_curve
    
    @property
    def component(self) -> CollarComponentDesign:
        """Collar component design parameters."""
        return self._component


class LeftDesign:
    """Design parameters for left/right asymmetric design.
    
    Attributes:
    -----------
    enable_asym : bool
        Whether to enable asymmetric design.
    shirt : TorsoDesign
        Shirt design parameters for left side (subset of full shirt design).
    collar : CollarDesign
        Collar design parameters for left side.
    sleeve : SleeveDesign
        Sleeve design parameters for left side.
    """
    
    def __init__(self, left_dict: dict) -> None:
        """Initialize left design from dictionary.
        
        Parameters:
        -----------
        left_dict : dict
            Dictionary containing left design parameters with 'v' keys.
        """
        self._enable_asym: bool = left_dict.get('enable_asym', {}).get('v', False)
        
        # Initialize nested designs
        shirt_dict = left_dict.get('shirt', {})
        self._shirt: TorsoDesign = TorsoDesign(shirt_dict)
        
        collar_dict = left_dict.get('collar', {})
        self._collar: CollarDesign = CollarDesign(collar_dict)
        
        sleeve_dict = left_dict.get('sleeve', {})
        self._sleeve: SleeveDesign = SleeveDesign(sleeve_dict)
    
    @property
    def enable_asym(self) -> bool:
        """Whether to enable asymmetric design."""
        return self._enable_asym
    
    @property
    def shirt(self) -> TorsoDesign:
        """Shirt design parameters for left side (subset of full shirt design)."""
        return self._shirt
    
    @property
    def collar(self) -> CollarDesign:
        """Collar design parameters for left side."""
        return self._collar
    
    @property
    def sleeve(self) -> SleeveDesign:
        """Sleeve design parameters for left side."""
        return self._sleeve


class ShirtDesign:
    """Design parameters for shirt garment.
    
    This class encapsulates all design parameters needed to construct shirt panels,
    replacing the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    shirt : TorsoDesign
        Shirt/torso design parameters (extends TorsoDesign with additional fields).
    collar : CollarDesign
        Collar design parameters.
    sleeve : SleeveDesign
        Sleeve design parameters.
    left : LeftDesign
        Left/right asymmetric design parameters.
    """
    
    def __init__(self, design_dict: dict) -> None:
        """Initialize shirt design from dictionary.
        
        Parameters:
        -----------
        design_dict : dict
            Dictionary containing shirt design parameters. The dictionary should
            contain 'shirt', 'collar', 'sleeve', and optionally 'left' keys.
            
            Each parameter should have a 'v' key containing the actual value.
        """
        # Initialize nested designs
        shirt_dict = design_dict.get('shirt', {})
        self._shirt: TorsoDesign = TorsoDesign(shirt_dict)
        
        collar_dict = design_dict.get('collar', {})
        self._collar: CollarDesign = CollarDesign(collar_dict)
        
        sleeve_dict = design_dict.get('sleeve', {})
        self._sleeve: SleeveDesign = SleeveDesign(sleeve_dict)
        
        left_dict = design_dict.get('left', {})
        self._left: LeftDesign = LeftDesign(left_dict)
    
    @property
    def shirt(self) -> TorsoDesign:
        """Shirt/torso design parameters (extends TorsoDesign with additional fields)."""
        return self._shirt
    
    @property
    def collar(self) -> CollarDesign:
        """Collar design parameters."""
        return self._collar
    
    @property
    def sleeve(self) -> SleeveDesign:
        """Sleeve design parameters."""
        return self._sleeve
    
    @property
    def left(self) -> LeftDesign:
        """Left/right asymmetric design parameters."""
        return self._left

