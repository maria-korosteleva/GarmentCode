from typing import Any

from config import SimulationControl, GarmentMaterialProperties, SimulationOptions

class SimConfig:
    """
    Combined simulation configuration that aggregates control, properties, and options.
    
    This class maintains backward compatibility by exposing all attributes directly,
    while internally delegating to specialized configuration classes. It provides
    a unified interface for accessing simulation control parameters, garment material
    properties, and simulation options.
    
    Attributes
    ----------
    _props : dict[str, Any]
        Original simulation properties dictionary
    _control : SimulationControl
        Simulation control and scheduler parameters (private)
    _properties : GarmentProperties
        Garment material and fabric properties (private)
    _options : SimulationOptions
        Feature flags and simulation behavior options (private)
    control : SimulationControl
        Simulation control and scheduler parameters (via property)
    properties : GarmentProperties
        Garment material and fabric properties (via property)
    options : SimulationOptions
        Feature flags and simulation behavior options (via property)
    props : dict[str, Any]
        Original simulation properties dictionary (via property)
    """
    
    # Class variable type annotations
    _props: dict[str, Any]
    _control: SimulationControl
    _properties: GarmentMaterialProperties
    _options: SimulationOptions
    
    def __init__(self, sim_props: dict[str, Any]) -> None:
        """
        Initialize simulation configuration from sim_props dict.
        
        Parameters
        ----------
        sim_props : dict[str, Any]
            Dictionary containing simulation configuration with sections:
            - 'control': Dict with simulation control parameters (timing, steps, etc.)
            - 'material': Dict with garment material/fabric properties
            - 'options': Dict with feature flags and simulation options
            
        Notes
        -----
        After initialization, all attributes from control, properties, and options
        are exposed at the top level for backward compatibility. For example:
        - config.sim_fps (from control)
        - config.garment_edge_ke (from properties)
        - config.enable_body_smoothing (from options)
        
        The YAML structure should have:
        ```yaml
        sim:
          config:
            control:
              sim_fps: 60.0
              max_sim_steps: 1000
              ...
            material:
              garment_edge_ke: 50000.0
              ...
            options:
              enable_body_smoothing: true
              ...
        ```
        """
        # Store original props
        self._props = sim_props
        
        # Extract sections - new structure has 'control', 'material', 'options' as separate sections
        # Support both new structure (with 'control' section) and old structure (top-level keys)
        if 'control' in sim_props:
            sim_props_control = sim_props['control']
        else:
            # Old structure: control params are at top level
            sim_props_control = {k: v for k, v in sim_props.items() 
                                if k not in ('material', 'options', 'optimize_storage', 'max_meshgen_time')}
        
        sim_props_material = sim_props.get('material', {})
        sim_props_option = sim_props.get('options', {})
        
        # Initialize specialized config classes using Pydantic models
        self._control = SimulationControl(**sim_props_control)
        self._properties = GarmentMaterialProperties(**sim_props_material)
        self._options = SimulationOptions(**sim_props_option)
        
        # Update smoothing steps based on max_sim_steps
        self._options.update_smoothing_steps(self._control.max_sim_steps)
        
        # Set body material properties from options
        self._properties.body_thickness = self._options.body_thickness
        self._properties.body_friction = self._options.body_friction
        
        # Update minimum steps based on options
        self._control.update_min_steps(self._options)
        
        # Expose all attributes for backward compatibility
        self._expose_attributes()

    @property
    def props(self) -> dict[str, Any]:
        """Original simulation properties dictionary."""
        return self._props
    
    @property
    def control(self) -> SimulationControl:
        """Simulation control and scheduler parameters."""
        return self._control
    
    @property
    def properties(self) -> GarmentMaterialProperties:
        """Garment material and fabric properties."""
        return self._properties
    
    @property
    def options(self) -> SimulationOptions:
        """Feature flags and simulation behavior options."""
        return self._options

    def _expose_attributes(self) -> None:
        """
        Expose all config attributes at the top level for backward compatibility.
        
        This method creates public attributes that directly reference the specialized
        config classes, allowing existing code to access attributes like config.sim_fps
        instead of config.control.sim_fps.
        """
        # Control attributes
        self.sim_fps = self._control.sim_fps
        self.sim_substeps = self._control.sim_substeps
        self.sim_wo_gravity_percentage = self._control.sim_wo_gravity_percentage
        self.zero_gravity_steps = self._control.zero_gravity_steps
        self.resolution_scale = self._control.resolution_scale
        self.ground = self._control.ground
        self.static_threshold = self._control.static_threshold
        self.max_sim_steps = self._control.max_sim_steps
        self.max_frame_time = self._control.max_frame_time
        self.max_sim_time = self._control.max_sim_time
        self.non_static_percent = self._control.non_static_percent
        self.max_body_collisions = self._control.max_body_collisions
        self.max_self_collisions = self._control.max_self_collisions
        self.min_sim_steps = self._control.min_sim_steps
        
        # Options attributes
        self.enable_particle_particle_collisions = self._options.enable_particle_particle_collisions
        self.enable_triangle_particle_collisions = self._options.enable_triangle_particle_collisions
        self.enable_edge_edge_collisions = self._options.enable_edge_edge_collisions
        self.enable_body_collision_filters = self._options.enable_body_collision_filters
        self.enable_attachment_constraint = self._options.enable_attachment_constraint
        self.attachment_constraints = self._options.attachment_constraints
        self.attachment_frames = self._options.attachment_frames
        # Backward compatibility: expose legacy attributes
        self.attachment_labels = [constraint.label for constraint in self._options.attachment_constraints]
        self.attachment_stiffness = [constraint.stiffness for constraint in self._options.attachment_constraints]
        self.attachment_damping = [constraint.damping for constraint in self._options.attachment_constraints]
        self.global_damping_factor = self._options.global_damping_factor
        self.global_damping_effective_velocity = self._options.global_damping_effective_velocity
        self.global_max_velocity = self._options.global_max_velocity
        self.enable_global_collision_filter = self._options.enable_global_collision_filter
        self.enable_cloth_reference_drag = self._options.enable_cloth_reference_drag
        self.cloth_reference_margin = self._options.cloth_reference_margin
        self.cloth_reference_k = self._options.cloth_reference_k
        self.enable_body_smoothing = self._options.enable_body_smoothing
        self.smoothing_total_smoothing_factor = self._options.smoothing_total_smoothing_factor
        self.smoothing_recover_start_frame = self._options.smoothing_recover_start_frame
        self.smoothing_frame_gap_between_steps = self._options.smoothing_frame_gap_between_steps
        self.smoothing_num_steps = self._options.smoothing_num_steps
        self.body_thickness = self._options.body_thickness
        self.body_friction = self._options.body_friction
        
        # Properties attributes
        self.garment_edge_ke = self._properties.garment_edge_ke
        self.garment_edge_kd = self._properties.garment_edge_kd
        self.garment_tri_ke = self._properties.garment_tri_ke
        self.garment_tri_kd = self._properties.garment_tri_kd
        self.garment_tri_ka = self._properties.garment_tri_ka
        self.garment_tri_drag = self._properties.garment_tri_drag
        self.garment_tri_lift = self._properties.garment_tri_lift
        self.garment_density = self._properties.garment_density
        self.garment_radius = self._properties.garment_radius
        self.spring_ke = self._properties.spring_ke
        self.spring_kd = self._properties.spring_kd
        self.soft_contact_margin = self._properties.soft_contact_margin
        self.soft_contact_ke = self._properties.soft_contact_ke
        self.soft_contact_kd = self._properties.soft_contact_kd
        self.soft_contact_kf = self._properties.soft_contact_kf
        self.soft_contact_mu = self._properties.soft_contact_mu
        self.particle_ke = self._properties.particle_ke
        self.particle_kd = self._properties.particle_kd
        self.particle_kf = self._properties.particle_kf
        self.particle_mu = self._properties.particle_mu
        self.particle_cohesion = self._properties.particle_cohesion
        self.particle_adhesion = self._properties.particle_adhesion

    def update_min_steps(self) -> None:
        """
        Update minimum simulation steps based on current options.
        
        Recalculates the minimum number of simulation steps required based on
        enabled features (body smoothing, attachment constraints, etc.) and
        updates both the internal control object and the exposed attribute.
        """
        self._control.update_min_steps(self._options)
        self.min_sim_steps = self._control.min_sim_steps
