"""Simulation control and scheduler parameters."""

from typing import Optional, Any
from pydantic import BaseModel, Field


class SimulationControl(BaseModel):
    """
    Parameters controlling simulation execution, timing, and stopping criteria.
    
    This class manages all aspects of simulation scheduling including frame rates,
    step limits, timeouts, and quality thresholds.
    
    Attributes
    ----------
    sim_fps : float
        Simulation frames per second
    sim_substeps : int
        Number of substeps per simulation frame
    sim_wo_gravity_percentage : float
        Percentage of simulation without gravity (0-100)
    zero_gravity_steps : int
        Number of initial steps to run without gravity
    resolution_scale : float
        Resolution scaling factor for mesh generation
    ground : bool
        Whether to include a ground plane in the simulation
    static_threshold : float
        Threshold for detecting static equilibrium (L1 norm per vertex)
    max_sim_steps : int
        Maximum number of simulation steps before timeout
    max_frame_time : Optional[int]
        Maximum time per frame in seconds (None for no limit)
    max_sim_time : int
        Maximum total simulation time in seconds
    non_static_percent : float
        Percentage of vertices that can be non-static before considering static
    max_body_collisions : int
        Maximum allowed body-cloth collisions before quality failure
    max_self_collisions : int
        Maximum allowed self-intersections before quality failure
    min_sim_steps : int
        Minimum number of simulation steps required (computed from options)
    """
    
    # Basic simulation setup
    sim_fps: float = Field(default=60.0, description="Simulation frames per second")
    sim_substeps: int = Field(default=10, description="Number of substeps per simulation frame")
    sim_wo_gravity_percentage: float = Field(default=0.0, description="Percentage of simulation without gravity (0-100)")
    zero_gravity_steps: int = Field(default=5, description="Number of initial steps to run without gravity")
    resolution_scale: float = Field(default=1.0, description="Resolution scaling factor for mesh generation")
    ground: bool = Field(default=True, description="Whether to include a ground plane in the simulation")

    # Stopping criteria
    static_threshold: float = Field(default=0.01, description="Threshold for detecting static equilibrium (L1 norm per vertex)")
    max_sim_steps: int = Field(default=1000, description="Maximum number of simulation steps before timeout")
    max_frame_time: Optional[int] = Field(default=None, description="Maximum time per frame in seconds (None for no limit)")
    max_sim_time: int = Field(default=1500, description="Maximum total simulation time in seconds")
    non_static_percent: float = Field(default=5.0, description="Percentage of vertices that can be non-static before considering static")
    
    # Quality filters
    max_body_collisions: int = Field(default=0, description="Maximum allowed body-cloth collisions before quality failure")
    max_self_collisions: int = Field(default=0, description="Maximum allowed self-intersections before quality failure")
    
    # Computed field (will be set by update_min_steps)
    min_sim_steps: int = Field(default=0, description="Minimum number of simulation steps required (computed from options)")

    model_config = {
        "frozen": False,  # Allow updates to min_sim_steps
    }

    def update_min_steps(self, options: Any) -> None:
        """
        Update minimum simulation steps based on options.
        
        Calculates the minimum number of steps required based on enabled features
        such as body smoothing and attachment constraints.
        
        Parameters
        ----------
        options : SimulationOptions
            Simulation options that may affect minimum steps. Uses:
            - enable_body_smoothing: If True, adds smoothing steps
            - smoothing_recover_start_frame: Frame to start recovery
            - smoothing_num_steps: Number of smoothing steps
            - enable_attachment_constraint: If True, adds attachment frames
            - attachment_frames: Number of frames for attachment
            
        Note
        ----
        Type hint uses Any to avoid circular import. Should be SimulationOptions.
        """
        min_steps = 0
        if options.enable_body_smoothing:
            min_steps = options.smoothing_recover_start_frame + options.smoothing_num_steps
        if options.enable_attachment_constraint:
            # NOTE: Adding a small number of frames 
            # to allow clothing movement to restart after attachment is released
            min_steps = max(min_steps, options.attachment_frames + 5)
        self.min_sim_steps = min_steps
