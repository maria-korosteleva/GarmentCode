"""Interface name definitions for garment components.

This module defines a StrEnum for all interface names used throughout
the garment programs to ensure type safety and maintainability.
"""

from enum import StrEnum


class InterfaceName(StrEnum):
    """Enumeration of all interface names used in garment components.
    
    This enum provides a centralized definition of all interface names
    to avoid string literal errors and improve code maintainability.
    """
    
    # Basic directional interfaces
    TOP = 'top'
    BOTTOM = 'bottom'
    LEFT = 'left'
    RIGHT = 'right'
    OUTSIDE = 'outside'
    INSIDE = 'inside'
    IN = 'in'
    OUT = 'out'
    
    # Shoulder and collar interfaces
    SHOULDER = 'shoulder'
    SHOULDER_CORNER = 'shoulder_corner'
    COLLAR_CORNER = 'collar_corner'
    FRONT_COLLAR = 'front_collar'
    BACK_COLLAR = 'back_collar'
    
    # Front/back specific interfaces
    FRONT_IN = 'front_in'
    BACK_IN = 'back_in'
    F_BOTTOM = 'f_bottom'
    B_BOTTOM = 'b_bottom'
    TOP_F = 'top_f'
    TOP_B = 'top_b'
    TOP_FRONT = 'top_front'
    TOP_BACK = 'top_back'
    BOTTOM_F = 'bottom_f'
    BOTTOM_B = 'bottom_b'
    
    # Crotch interfaces (for pants)
    CROTCH = 'crotch'
    CROTCH_F = 'crotch_f'
    CROTCH_B = 'crotch_b'
    
    # Sleeve interfaces
    IN_FRONT_SHAPE = 'in_front_shape'
    IN_BACK_SHAPE = 'in_back_shape'
    
    # Collar projection interfaces
    FRONT_PROJ = 'front_proj'
    BACK_PROJ = 'back_proj'
    
    # Collar-specific interfaces
    TO_COLLAR = 'to_collar'
    TO_BODICE = 'to_bodice'
    TO_OTHER_SIDE = 'to_other_side'
    FRONT = 'front'
    BACK = 'back'


class EdgeLabel(StrEnum):
    """Enumeration of all edge labels used in garment components.
    
    This enum provides a centralized definition of all edge labels
    to avoid string literal errors and improve code maintainability.
    """
    
    # Interface attachment labels
    LOWER_INTERFACE = 'lower_interface'
    STRAPLESS_TOP = 'strapless_top'
    
    # Seam labels
    CROTCH_POINT_SEAM = 'crotch_point_seam'
    
    # Component-specific labels (used with f-strings)
    ARMHOLE = 'armhole'
    COLLAR = 'collar'


class PanelLabel(StrEnum):
    """Enumeration of all panel labels used in garment components.
    
    This enum provides a centralized definition of all panel labels
    to avoid string literal errors and improve code maintainability.
    """
    
    BODY = 'body'
    LEG = 'leg'
    ARM = 'arm'

