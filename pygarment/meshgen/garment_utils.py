"""Utility functions for garment simulation."""

from typing import Any

import warp as wp
from loguru import logger
from pattern_definitions.body_definition import BodyDefinition
from pygarment.meshgen.box_mesh_gen.stitch_types import EdgeLabel


class AttachmentConstraintUtils:
    """Static utility methods for attachment constraint calculations."""
    
    @staticmethod
    def calculate_position_from_body_params(
        position_calc: dict[str, dict[str, list[str]]],
        body_def: BodyDefinition
    ) -> wp.vec3:
        """Calculate position vector from body parameters using positive/negative lists.
        
        For each axis (x, y, z), calculates: sum(positive_params) - sum(negative_params)
        
        Parameters
        ----------
        position_calc : dict[str, dict[str, list[str]]]
            Position calculation specification with 'x', 'y', 'z' keys, each containing
            a dictionary with 'positive' and 'negative' lists of body parameter names.
            Example: {'x': {'positive': ['param1'], 'negative': ['param2']}, ...}
        body_def : BodyDefinition
            Body definition object to access parameters.
        
        Returns
        -------
        wp.vec3
            Calculated position vector [x, y, z].
            
        Note
        ----
        If a body parameter is not found, a warning is logged and 0.0 is used
        as the default value for that parameter.
        """
        def get_body_param_value(param_name: str) -> float:
            """Get body parameter value, handling both direct and computed properties.
            
            Parameters
            ----------
            param_name : str
                Name of the body parameter to retrieve.
                
            Returns
            -------
            float
                Parameter value, or 0.0 if not found.
            """
            try:
                return body_def[param_name]
            except KeyError:
                logger.warning(f'Body parameter "{param_name}" not found, using 0.0')
                return 0.0
        
        def calculate_axis(axis_params: dict[str, list[str]]) -> float:
            """Calculate single axis value from positive and negative parameter lists.
            
            Parameters
            ----------
            axis_params : dict[str, list[str]]
                Dictionary with 'positive' and 'negative' keys containing lists
                of parameter names.
                
            Returns
            -------
            float
                Calculated axis value: sum(positive) - sum(negative).
            """
            positive_sum = sum(get_body_param_value(param) for param in axis_params.get('positive', []))
            negative_sum = sum(get_body_param_value(param) for param in axis_params.get('negative', []))
            return positive_sum - negative_sum
        
        x = calculate_axis(position_calc.get('x', {'positive': [], 'negative': []}))
        y = calculate_axis(position_calc.get('y', {'positive': [], 'negative': []}))
        z = calculate_axis(position_calc.get('z', {'positive': [], 'negative': []}))
        
        return wp.vec3(x, y, z)
    
    @staticmethod
    def get_default_position_for_label(label: EdgeLabel | str, body_def: BodyDefinition) -> wp.vec3 | None:
        """
        Get default position for a label type using BodyDefinition.
        
        Parameters
        ----------
        label : EdgeLabel | str
            Attachment label enum or string value.
        body_def : BodyDefinition
            Body definition object.
        
        Returns
        -------
        wp.vec3 | None
            Default position vector, or None if label is not supported.
        """
        # Convert EdgeLabel to string value if needed
        label_str = label.value if isinstance(label, EdgeLabel) else label
        
        if label_str == EdgeLabel.CROTCH.value:
            crotch_level = body_def['_leg_length'] - body_def['crotch_hip_diff']
            return wp.vec3(0, crotch_level, 0)
        elif label_str == EdgeLabel.LOWER_INTERFACE.value:
            try:
                waist_level = body_def['_waist_level']
            except KeyError:
                waist_level = body_def['computed_waist_level']
            return wp.vec3(0, waist_level, 0)
        elif label_str == EdgeLabel.RIGHT_COLLAR.value:
            neck_w = body_def['neck_w'] - 2
            return wp.vec3(-neck_w / 2, 0, 0)
        elif label_str == EdgeLabel.LEFT_COLLAR.value:
            neck_w = body_def['neck_w'] - 2
            return wp.vec3(neck_w / 2, 0, 0)
        elif label_str == EdgeLabel.STRAPLESS_TOP.value:
            level = body_def['height'] - body_def['head_l'] - body_def['armscye_depth']
            return wp.vec3(0, level, 0)
        else:
            return None
    
    @staticmethod
    def get_default_direction_for_label(label: EdgeLabel | str) -> wp.vec3:
        """
        Get default direction vector for a label type.
        
        Parameters
        ----------
        label : EdgeLabel | str
            Attachment label enum or string value.
        
        Returns
        -------
        wp.vec3
            Default direction vector.
        """
        # Convert EdgeLabel to string value if needed
        label_str = label.value if isinstance(label, EdgeLabel) else label
        
        defaults = {
            EdgeLabel.CROTCH.value: wp.vec3(0., -1., 0.),  # Vertical attachment downward
            EdgeLabel.LOWER_INTERFACE.value: wp.vec3(0., 1., 0.),  # Vertical attachment upward
            EdgeLabel.RIGHT_COLLAR.value: wp.vec3(1., 0., 0.),  # Horizontal attachment right
            EdgeLabel.LEFT_COLLAR.value: wp.vec3(-1., 0., 0.),  # Horizontal attachment left
            EdgeLabel.STRAPLESS_TOP.value: wp.vec3(0., 1., 0.),  # Vertical attachment upward
        }
        return defaults.get(label_str, wp.vec3(0., 1., 0.))  # Default upward

