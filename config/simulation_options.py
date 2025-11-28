"""Simulation options and feature flags."""

from typing import Any, List

from pydantic import BaseModel, Field, model_validator, field_validator


class AttachmentConstraint(BaseModel):
    """
    Represents a single attachment constraint configuration.
    
    Attributes
    ----------
    label : EdgeLabel
        Attachment label enum (e.g., EdgeLabel.CROTCH, EdgeLabel.LOWER_INTERFACE).
        This is the final label that will be used to identify vertices in the mesh.
    vertex_labels_to_find : List[EdgeLabel]
        List of edge labels to search for in the mesh to find reference vertices.
        These labels are used to locate vertices that will then be processed by
        the garment program to determine the final set of vertices for this constraint.
        For example, [EdgeLabel.CROTCH_POINT_SEAM] finds edges with that label,
        then the garment program can use those vertices to label all vertices below them.
    stiffness : float
        Stiffness value for this attachment constraint
    damping : float
        Damping value for this attachment constraint
    position : list[float] | None
        Optional explicit position vector [x, y, z] for attachment point. If provided,
        this overrides position_calculation. If None, position is calculated from
        position_calculation or label-specific defaults.
    direction : list[float] | None
        Optional direction vector [x, y, z] for attachment direction. If None, uses
        label-specific default direction.
    position_calculation : dict[str, dict[str, list[str]]] | None
        Optional position calculation specification. If provided, position is calculated
        as: sum(positive_params) - sum(negative_params) for each axis.
        Format: {
            'x': {'positive': [param_names], 'negative': [param_names]},
            'y': {'positive': [param_names], 'negative': [param_names]},
            'z': {'positive': [param_names], 'negative': [param_names]}
        }
        Body parameter names can include computed properties (e.g., 'computed_leg_length',
        '_leg_length' for legacy format).
    """
    label: Any = Field(description="Attachment label enum (e.g., EdgeLabel.CROTCH, EdgeLabel.LOWER_INTERFACE)")
    vertex_labels_to_find: List[Any] = Field(
        default_factory=list,
        description="List of edge labels to search for in the mesh to find reference vertices"
    )
    stiffness: float = Field(description="Stiffness value for this attachment constraint")
    damping: float = Field(description="Damping value for this attachment constraint")
    position: list[float] | None = Field(
        default=None,
        description="Optional explicit position vector [x, y, z]. Overrides position_calculation if provided."
    )
    direction: list[float] | None = Field(
        default=None,
        description="Optional direction vector [x, y, z] for attachment direction. If None, uses label-specific default."
    )
    position_calculation: dict[str, dict[str, list[str]]] | None = Field(
        default=None,
        description="Position calculation from body parameters. Format: {'x': {'positive': [...], 'negative': [...]}, ...}"
    )
    
    @field_validator('label', mode='before')
    @classmethod
    def validate_label(cls, v):
        """Convert string labels to EdgeLabel enum for backward compatibility."""
        # Import here to avoid circular import
        from pygarment.meshgen.box_mesh_gen.stitch_types import EdgeLabel
        
        if isinstance(v, str):
            try:
                return EdgeLabel(v)
            except ValueError:
                raise ValueError(f'Invalid label: {v}. Must be a valid EdgeLabel enum value.')
        # If it's already an EdgeLabel, return as-is
        return v
    
    @field_validator('vertex_labels_to_find', mode='before')
    @classmethod
    def validate_vertex_labels_to_find(cls, v):
        """Convert string labels to EdgeLabel enums for backward compatibility."""
        # Import here to avoid circular import
        from pygarment.meshgen.box_mesh_gen.stitch_types import EdgeLabel
        
        if v is None:
            return []
        if isinstance(v, list):
            return [EdgeLabel(item) if isinstance(item, str) else item for item in v]
        return v
    
    @property
    def label_enum(self):  # type: ignore[no-any-return]
        """Get the label as an EdgeLabel enum.
        
        After validation, label is always an EdgeLabel enum, so we can return it directly.
        
        Returns
        -------
        EdgeLabel
            The label as an EdgeLabel enum.
        """
        # Validator ensures this is always EdgeLabel after validation
        # Return directly - validators guarantee type consistency
        return self.label
    
    @property
    def vertex_labels_to_find_enums(self):  # type: ignore[no-any-return]
        """Get vertex_labels_to_find as a list of EdgeLabel enums.
        
        After validation, all items are EdgeLabel enums, so we can return them directly.
        
        Returns
        -------
        List[EdgeLabel]
            List of EdgeLabel enums.
        """
        # Validator ensures all items are EdgeLabel enums after validation
        # Return directly - validators guarantee type consistency
        return self.vertex_labels_to_find
    
    @field_validator('position')
    @classmethod
    def validate_position(cls, v):
        if v is not None and len(v) != 3:
            raise ValueError('position must be a list of exactly 3 floats [x, y, z]')
        return v
    
    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v):
        if v is not None and len(v) != 3:
            raise ValueError('direction must be a list of exactly 3 floats [x, y, z]')
        return v
    
    @field_validator('position_calculation')
    @classmethod
    def validate_position_calculation(cls, v):
        if v is not None:
            for axis in ['x', 'y', 'z']:
                if axis not in v:
                    raise ValueError(f'position_calculation must include {axis} axis')
                if 'positive' not in v[axis] or 'negative' not in v[axis]:
                    raise ValueError(f'position_calculation[{axis}] must have "positive" and "negative" keys')
                if not isinstance(v[axis]['positive'], list) or not isinstance(v[axis]['negative'], list):
                    raise ValueError(f'position_calculation[{axis}]["positive"] and ["negative"] must be lists')
        return v


class SimulationOptions(BaseModel):
    """
    Feature flags and options for simulation behavior.
    
    This class manages all simulation feature toggles including collision detection
    methods, attachment constraints, damping, body smoothing, and other behavioral
    options.
    
    Attributes
    ----------
    edge_contact_max : int
        Maximum number of edge contacts per spring, gets multiplied by 3 for edge-edge collisions
    enable_particle_particle_collisions : bool
        Enable particle-particle collision detection
    enable_triangle_particle_collisions : bool
        Enable triangle-particle collision detection
    enable_edge_edge_collisions : bool
        Enable edge-edge collision detection
    enable_body_collision_filters : bool
        Enable body collision filters for selective collision detection
    enable_attachment_constraint : bool
        Enable attachment constraints for garment-body attachment
    attachment_constraints : list[AttachmentConstraint]
        List of attachment constraint configurations
    attachment_frames : int
        Number of frames to maintain attachment constraints
    global_damping_factor : float
        Global damping factor for velocity damping
    global_damping_effective_velocity : float
        Minimum velocity threshold for global damping to take effect
    global_max_velocity : float
        Maximum allowed velocity (clamped after damping)
    enable_global_collision_filter : bool
        Enable global collision filtering
    enable_cloth_reference_drag : bool
        Enable cloth reference drag for collision resolution
    cloth_reference_margin : float
        Margin for cloth reference drag collision detection
    cloth_reference_k : float
        Stiffness coefficient for cloth reference drag
    enable_body_smoothing : bool
        Enable progressive body smoothing (starts smooth, recovers detail)
    smoothing_total_smoothing_factor : float
        Total smoothing factor applied to body mesh
    smoothing_recover_start_frame : int
        Frame number to start recovering body detail from smoothing
    smoothing_frame_gap_between_steps : int
        Number of frames between smoothing recovery steps
    smoothing_num_steps : int
        Number of steps to gradually recover body detail
    body_thickness : float
        Body collision thickness
    body_friction : float
        Body friction coefficient
    """
    
    # Self-collision prevention properties
    edge_contact_max: int = Field(default=1024, description="Maximum number of edge contacts per spring, gets multiplied by 3 for edge-edge collisions")
    enable_particle_particle_collisions: bool = Field(default=False, description="Enable particle-particle collision detection")
    enable_triangle_particle_collisions: bool = Field(default=False, description="Enable triangle-particle collision detection")
    enable_edge_edge_collisions: bool = Field(default=False, description="Enable edge-edge collision detection")
    enable_body_collision_filters: bool = Field(default=False, description="Enable body collision filters for selective collision detection")

    # Attachment constraints
    enable_attachment_constraint: bool = Field(default=False, description="Enable attachment constraints for garment-body attachment")
    attachment_constraints: list[AttachmentConstraint] = Field(
        default_factory=list,
        description="List of attachment constraint configurations"
    )
    attachment_frames: int = Field(default=100, description="Number of frames to maintain attachment constraints")
    
    # Legacy fields for backward compatibility (deprecated, use attachment_constraints instead)
    attachment_labels: list[str] | None = Field(
        default=None,
        alias='attachment_label_names',
        description="[DEPRECATED] List of attachment label names. Use attachment_constraints instead."
    )
    attachment_stiffness: list[float] | None = Field(
        default=None,
        description="[DEPRECATED] Stiffness values for each attachment constraint. Use attachment_constraints instead."
    )
    attachment_damping: list[float] | None = Field(
        default=None,
        description="[DEPRECATED] Damping values for each attachment constraint. Use attachment_constraints instead."
    )

    # Global damping properties
    global_damping_factor: float = Field(default=1.0, description="Global damping factor for velocity damping")
    global_damping_effective_velocity: float = Field(default=0.0, description="Minimum velocity threshold for global damping to take effect")
    global_max_velocity: float = Field(default=50.0, description="Maximum allowed velocity (clamped after damping)")

    # Cloth global collision resolution (reference drag) options
    enable_global_collision_filter: bool = Field(default=False, description="Enable global collision filtering")
    enable_cloth_reference_drag: bool = Field(default=False, description="Enable cloth reference drag for collision resolution")
    cloth_reference_margin: float = Field(default=0.1, description="Margin for cloth reference drag collision detection")
    cloth_reference_k: float = Field(default=1.0e7, description="Stiffness coefficient for cloth reference drag")

    # Body smoothing options
    enable_body_smoothing: bool = Field(default=True, description="Enable progressive body smoothing (starts smooth, recovers detail)")
    smoothing_total_smoothing_factor: float = Field(default=1.0, description="Total smoothing factor applied to body mesh")
    smoothing_recover_start_frame: int = Field(default=0, description="Frame number to start recovering body detail from smoothing")
    smoothing_frame_gap_between_steps: int = Field(default=5, description="Number of frames between smoothing recovery steps")
    smoothing_num_steps: int = Field(default=100, description="Number of steps to gradually recover body detail")

    # Body material (collision properties)
    body_thickness: float = Field(
        default=0.0, 
        alias='body_collision_thickness',
        description="Body collision thickness"
    )
    body_friction: float = Field(default=0.5, description="Body friction coefficient")

    model_config = {
        "frozen": False,  # Allow updates to smoothing_num_steps and enable_body_smoothing
        "populate_by_name": True,  # Allow both 'attachment_labels' and 'attachment_label_names'
    }

    @model_validator(mode='after')
    def _convert_legacy_attachment_format(self) -> 'SimulationOptions':
        """
        Convert legacy format (parallel lists) to new AttachmentConstraint format.
        
        Supports backward compatibility with YAML files that use:
        - attachment_label_names: [list of strings]
        - attachment_stiffness: [list of floats]
        - attachment_damping: [list of floats]
        
        These are converted to attachment_constraints: [list of AttachmentConstraint objects]
        """
        # If attachment_constraints is already populated, use it
        if self.attachment_constraints:
            return self
        
        # If legacy fields are present, convert them
        if (self.attachment_labels is not None and 
            self.attachment_stiffness is not None and 
            self.attachment_damping is not None):
            
            labels = self.attachment_labels
            stiffnesses = self.attachment_stiffness
            dampings = self.attachment_damping
            
            # Validate that all lists have the same length
            if len(labels) != len(stiffnesses) or len(labels) != len(dampings):
                raise ValueError(
                    f"attachment_labels ({len(labels)}), attachment_stiffness ({len(stiffnesses)}), "
                    f"and attachment_damping ({len(dampings)}) must have the same length"
                )
            
            # Convert to AttachmentConstraint objects
            # Convert string labels to EdgeLabel enums
            from pygarment.meshgen.box_mesh_gen.stitch_types import EdgeLabel
            
            self.attachment_constraints = [
                AttachmentConstraint(
                    label=EdgeLabel(label) if isinstance(label, str) else label,
                    stiffness=stiff,
                    damping=damp
                )
                for label, stiff, damp in zip(labels, stiffnesses, dampings)
            ]
        
        return self

    def model_post_init(self, __context) -> None:
        """Post-initialization validation: disable attachment constraint if frames or constraints are missing."""
        if not self.attachment_frames or not self.attachment_constraints:
            self.enable_attachment_constraint = False

    def update_smoothing_steps(self, max_sim_steps: int) -> None:
        """
        Update smoothing steps based on max simulation steps.
        
        Adjusts the number of smoothing steps to ensure they don't exceed the
        maximum simulation steps. Disables body smoothing if no steps remain.
        
        Parameters
        ----------
        max_sim_steps : int
            Maximum simulation steps available
        """
        self.smoothing_num_steps = max(min(
            self.smoothing_num_steps, 
            max_sim_steps - self.smoothing_recover_start_frame),
            0)
        if self.smoothing_num_steps == 0:
            self.enable_body_smoothing = False
