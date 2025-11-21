"""Simulation options and feature flags."""

from pydantic import BaseModel, Field


class SimulationOptions(BaseModel):
    """
    Feature flags and options for simulation behavior.
    
    This class manages all simulation feature toggles including collision detection
    methods, attachment constraints, damping, body smoothing, and other behavioral
    options.
    
    Attributes
    ----------
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
    attachment_labels : list[str]
        List of attachment label names (e.g., 'crotch', 'lower_interface')
    attachment_frames : int
        Number of frames to maintain attachment constraints
    attachment_stiffness : list[float]
        Stiffness values for each attachment constraint
    attachment_damping : list[float]
        Damping values for each attachment constraint
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
    enable_particle_particle_collisions: bool = Field(default=False, description="Enable particle-particle collision detection")
    enable_triangle_particle_collisions: bool = Field(default=False, description="Enable triangle-particle collision detection")
    enable_edge_edge_collisions: bool = Field(default=False, description="Enable edge-edge collision detection")
    enable_body_collision_filters: bool = Field(default=False, description="Enable body collision filters for selective collision detection")

    # Attachment constraints
    enable_attachment_constraint: bool = Field(default=False, description="Enable attachment constraints for garment-body attachment")
    attachment_labels: list[str] = Field(
        default_factory=list, 
        alias='attachment_label_names',
        description="List of attachment label names (e.g., 'crotch', 'lower_interface')"
    )
    attachment_frames: int = Field(default=100, description="Number of frames to maintain attachment constraints")
    attachment_stiffness: list[float] = Field(default_factory=list, description="Stiffness values for each attachment constraint")
    attachment_damping: list[float] = Field(default_factory=list, description="Damping values for each attachment constraint")

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

    def model_post_init(self, __context) -> None:
        """Post-initialization validation: disable attachment constraint if frames or labels are missing."""
        if not self.attachment_frames or not self.attachment_labels:
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
