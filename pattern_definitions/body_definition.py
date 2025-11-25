"""Body parameter class definition.

This module defines the BodyDefinition class that encapsulates all body parameters
for garment construction, replacing the previous dictionary-based approach.
"""


class BodyDefinition:
    """Body measurements and computed parameters for garment construction.
    
    This class encapsulates all body measurements needed for constructing garments,
    including both direct measurements and computed derived parameters. It replaces
    the dictionary-based parameter access pattern.
    
    Attributes:
    -----------
    # Direct measurements
    arm_length : float
        Length of the arm.
    arm_pose_angle : float
        Angle of arm pose.
    armscye_depth : float
        Depth of the armscye (armhole).
    back_width : float
        Width of the back.
    bum_points : float
        Bum points measurement.
    bust : float
        Bust circumference.
    bust_line : float
        Vertical position of bust line.
    bust_points : float
        Bust points measurement.
    crotch_hip_diff : float
        Vertical difference between crotch and hip line.
    head_l : float
        Length of the head.
    height : float
        Total body height.
    hip_back_width : float
        Back width at hip level.
    hip_inclination : float
        Inclination angle of hips.
    hips : float
        Hip circumference.
    hips_line : float
        Vertical position of hip line.
    leg_circ : float
        Leg circumference.
    neck_w : float
        Neck width.
    shoulder_incl : float
        Shoulder inclination angle.
    shoulder_w : float
        Shoulder width.
    underbust : float
        Underbust circumference.
    vert_bust_line : float
        Vertical bust line position.
    waist : float
        Waist circumference.
    waist_back_width : float
        Back width at waist level.
    waist_line : float
        Vertical position of waist line.
    waist_over_bust_line : float
        Waist over bust line measurement.
    wrist : float
        Wrist circumference.
    
    # Computed parameters (accessed via properties)
    computed_waist_level : float
        Computed vertical position of waist level (height - head_l - waist_line).
    computed_leg_length : float
        Computed leg length (computed_waist_level - hips_line).
    computed_base_sleeve_balance : float
        Computed base sleeve balance (shoulder_w - 2).
    computed_bust_line : float
        Computed adjusted bust line position.
    computed_hip_inclination : float
        Computed half hip inclination (hip_inclination / 2).
    computed_shoulder_incl : float
        Computed shoulder inclination (same as shoulder_incl).
    computed_armscye_depth : float
        Computed armscye depth with ease (armscye_depth + 2.5).
    """
    
    def __init__(self, body_dict: dict) -> None:
        """Initialize body definition from dictionary.
        
        Parameters:
        -----------
        body_dict : dict
            Dictionary containing body parameters. Can be either:
            - The full body dict (will extract 'body' key if present)
            - The 'body' sub-dictionary directly
            - A BodyParameters.params dict
            
            Parameters can be direct values or wrapped in 'v' keys.
        """
        # Handle both full body dict and body sub-dict
        if 'body' in body_dict and isinstance(body_dict['body'], dict):
            # Check if it's a nested structure with 'v' keys or direct values
            first_key = next(iter(body_dict['body'].values()), None)
            if isinstance(first_key, dict) and 'v' in first_key:
                # It's a design-style dict with 'v' keys
                body_dict = body_dict['body']
            else:
                # It's a direct value dict
                body_dict = body_dict['body']
        
        # Extract direct measurements with safe defaults
        # Handle both direct values and {'v': value} format
        def _get_value(key: str, default: float = 0.0) -> float:
            """Helper to extract value from either format."""
            if key in body_dict:
                val = body_dict[key]
                if isinstance(val, dict) and 'v' in val:
                    return val['v']
                elif isinstance(val, (int, float)):
                    return float(val)
            return default
        
        self.arm_length: float = _get_value('arm_length', 0.0)
        self.arm_pose_angle: float = _get_value('arm_pose_angle', 0.0)
        self.armscye_depth: float = _get_value('armscye_depth', 0.0)
        self.back_width: float = _get_value('back_width', 0.0)
        self.bum_points: float = _get_value('bum_points', 0.0)
        self.bust: float = _get_value('bust', 0.0)
        self.bust_line: float = _get_value('bust_line', 0.0)
        self.bust_points: float = _get_value('bust_points', 0.0)
        self.crotch_hip_diff: float = _get_value('crotch_hip_diff', 0.0)
        self.head_l: float = _get_value('head_l', 0.0)
        self.height: float = _get_value('height', 0.0)
        self.hip_back_width: float = _get_value('hip_back_width', 0.0)
        self.hip_inclination: float = _get_value('hip_inclination', 0.0)
        self.hips: float = _get_value('hips', 0.0)
        self.hips_line: float = _get_value('hips_line', 0.0)
        self.leg_circ: float = _get_value('leg_circ', 0.0)
        self.neck_w: float = _get_value('neck_w', 0.0)
        self.shoulder_incl: float = _get_value('shoulder_incl', 0.0)
        self.shoulder_w: float = _get_value('shoulder_w', 0.0)
        self.underbust: float = _get_value('underbust', 0.0)
        self.vert_bust_line: float = _get_value('vert_bust_line', 0.0)
        self.waist: float = _get_value('waist', 0.0)
        self.waist_back_width: float = _get_value('waist_back_width', 0.0)
        self.waist_line: float = _get_value('waist_line', 0.0)
        self.waist_over_bust_line: float = _get_value('waist_over_bust_line', 0.0)
        self.wrist: float = _get_value('wrist', 0.0)
        self._fit_waist_level: float = self.computed_waist_level
    
    @property
    def computed_waist_level(self) -> float:
        """Computed vertical position of waist level (height - head_l - waist_line)."""
        return self.height - self.head_l - self.waist_line

    @property
    def fit_waist_level(self) -> float:
        return self._fit_waist_level

    @fit_waist_level.setter
    def fit_waist_level(self, value: float) -> None:
        self._fit_waist_level = value

    @property
    def computed_leg_length(self) -> float:
        """Computed leg length (computed_waist_level - hips_line)."""
        return self.computed_waist_level - self.hips_line
    
    @property
    def computed_base_sleeve_balance(self) -> float:
        """Computed base sleeve balance (shoulder_w - 2)."""
        return self.shoulder_w - 2
    
    @property
    def computed_bust_line(self) -> float:
        """Computed adjusted bust line position."""
        if self.vert_bust_line > 0:
            return (1 - 1/3) * self.vert_bust_line + 1/3 * self.bust_line
        else:
            return self.bust_line
    
    @property
    def computed_hip_inclination(self) -> float:
        """Computed half hip inclination (hip_inclination / 2)."""
        return self.hip_inclination / 2
    
    @property
    def computed_shoulder_incl(self) -> float:
        """Computed shoulder inclination (same as shoulder_incl)."""
        return self.shoulder_incl
    
    @property
    def computed_armscye_depth(self) -> float:
        """Computed armscye depth with ease (armscye_depth + 2.5)."""
        return self.armscye_depth + 2.5
    
    def __getitem__(self, key: str) -> float:
        """Support dict-like access for backward compatibility.
        
        Parameters:
        -----------
        key : str
            The body parameter key to access. Supports both direct attributes
            and computed properties (with 'computed_' prefix or '_' prefix).
        
        Returns:
        --------
        float
            The requested body parameter value.
        
        Raises:
        -------
        KeyError
            If the key is not found.
        """
        # Handle computed properties with '_' prefix (legacy format)
        if key.startswith('_'):
            # Remove '_' and check if it's a computed property
            computed_key = key[1:]
            if hasattr(self, f'computed_{computed_key}'):
                return getattr(self, f'computed_{computed_key}')
            # Some legacy keys use '_' prefix directly
            if computed_key == 'waist_level':
                return self.computed_waist_level
            elif computed_key == 'bust_line':
                return self.computed_bust_line
            elif computed_key == 'base_sleeve_balance':
                return self.computed_base_sleeve_balance
            elif computed_key == 'shoulder_incl':
                return self.computed_shoulder_incl
            elif computed_key == 'armscye_depth':
                return self.computed_armscye_depth
            elif computed_key == 'hip_inclination':
                return self.computed_hip_inclination
        
        # Handle direct attributes
        if hasattr(self, key):
            return getattr(self, key)
        
        # Handle computed properties with 'computed_' prefix
        if hasattr(self, f'computed_{key}'):
            return getattr(self, f'computed_{key}')
        
        raise KeyError(f"Body parameter '{key}' not found")

