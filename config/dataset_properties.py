"""Dataset properties configuration classes."""

from typing import Any, Optional
from pydantic import BaseModel, Field

from config.sim_config import SimConfig
from config.render_config import RenderConfig


class SimulationProperties(BaseModel):
    """Simulation properties containing config and statistics.
    
    Attributes
    ----------
    config : dict[str, Any]
        Simulation configuration dictionary (used to create SimConfig)
    stats : dict[str, Any]
        Simulation statistics dictionary
    """
    config: dict[str, Any] = Field(description="Simulation configuration dictionary")
    stats: dict[str, Any] = Field(default_factory=dict, description="Simulation statistics dictionary")
    
    def get_sim_config(self) -> SimConfig:
        """Get SimConfig instance from config dictionary.
        
        Returns
        -------
        SimConfig
            Initialized SimConfig object
        """
        return SimConfig(self.config)
    
    def get_optional_config_value(self, key: str, default: Any = None) -> Any:
        """Get an optional config value that's not part of SimConfig classes.
        
        Some config values like 'max_meshgen_time', 'optimize_storage' are stored
        in the config dict but not part of the structured config classes. This method
        provides safe access to those values.
        
        Parameters
        ----------
        key : str
            Key to look up in the config dictionary
        default : Any, optional
            Default value if key is not found. Default is None.
            
        Returns
        -------
        Any
            The config value or default if not found
        """
        return self.config.get(key, default)
    
    def get_options_dict(self) -> dict[str, Any]:
        """Get the options section as a dictionary.
        
        Some optional fields like 'store_vertex_normals' and 'store_panels' are
        stored in the options dict but not part of SimulationOptions. This method
        provides access to the full options dict.
        
        Returns
        -------
        dict[str, Any]
            The options dictionary from config
        """
        return self.config.get('options', {})


class RenderProperties(BaseModel):
    """Render properties containing config and statistics.
    
    Attributes
    ----------
    config : RenderConfig
        Render configuration object
    stats : dict[str, Any]
        Render statistics dictionary
    """
    config: RenderConfig = Field(description="Render configuration object")
    stats: dict[str, Any] = Field(default_factory=dict, description="Render statistics dictionary")
    
    @classmethod
    def from_dict(cls, render_dict: dict[str, Any]) -> 'RenderProperties':
        """Create RenderProperties from dictionary.
        
        Parameters
        ----------
        render_dict : dict[str, Any]
            Dictionary with 'config' and optional 'stats' keys
            
        Returns
        -------
        RenderProperties
            Initialized RenderProperties object
        """
        config_dict = render_dict.get('config', {})
        # Handle nested uv_texture if it's a dict
        if 'uv_texture' in config_dict and isinstance(config_dict['uv_texture'], dict):
            from config.render_config import UVTextureConfig
            config_dict['uv_texture'] = UVTextureConfig(**config_dict['uv_texture'])
        
        render_config = RenderConfig(**config_dict)
        stats = render_dict.get('stats', {})
        
        return cls(config=render_config, stats=stats)


class DatasetProperties(BaseModel):
    """Dataset properties containing simulation and render configurations.
    
    This class wraps the top-level properties structure that contains both
    simulation and render configurations. It provides type-safe access to
    both sections.
    
    Attributes
    ----------
    sim : SimulationProperties
        Simulation properties (config + stats)
    render : RenderProperties
        Render properties (config + stats)
    """
    sim: SimulationProperties = Field(description="Simulation properties")
    render: RenderProperties = Field(description="Render properties")
    
    @classmethod
    def from_props(cls, props: Any) -> 'DatasetProperties':
        """Create DatasetProperties from Properties object.
        
        Parameters
        ----------
        props : Any
            Properties object (dict-like) with 'sim' and 'render' keys
            
        Returns
        -------
        DatasetProperties
            Initialized DatasetProperties object
        """
        sim_dict = props['sim'] if isinstance(props, dict) else props['sim']
        render_dict = props['render'] if isinstance(props, dict) else props['render']
        
        sim_props = SimulationProperties(**sim_dict)
        render_props = RenderProperties.from_dict(render_dict)
        
        return cls(sim=sim_props, render=render_props)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with Properties object.
        
        Returns
        -------
        dict[str, Any]
            Dictionary with 'sim' and 'render' keys
        """
        return {
            'sim': {
                'config': self.sim.config,
                'stats': self.sim.stats
            },
            'render': {
                'config': self.render.config.model_dump(),
                'stats': self.render.stats
            }
        }
    
    def update_props(self, props: Any) -> None:
        """Update the underlying Properties object with current values.
        
        This method writes the current config and stats back to the props object,
        allowing modifications made to DatasetProperties to be persisted.
        
        Parameters
        ----------
        props : Any
            Properties object (dict-like) to update
        """
        # Update sim config and stats
        props['sim']['config'] = self.sim.config
        props['sim']['stats'] = self.sim.stats
        
        # Update render config and stats
        props['render']['config'] = self.render.config.model_dump()
        props['render']['stats'] = self.render.stats
    
    def update_sim_config(self, sim_config: SimConfig) -> None:
        """Update simulation configuration from SimConfig object.
        
        This method updates the internal config dictionary with values from
        a SimConfig object. Useful when you've modified SimConfig attributes
        and want to persist those changes.
        
        Parameters
        ----------
        sim_config : SimConfig
            SimConfig object containing updated configuration values
        """
        # Update the config dict with values from SimConfig
        # We need to reconstruct the dict structure
        config_dict = {}
        
        # Add control section
        if hasattr(sim_config, '_control'):
            config_dict['control'] = sim_config._control.model_dump()
        
        # Add material section
        if hasattr(sim_config, '_properties'):
            config_dict['material'] = sim_config._properties.model_dump()
        
        # Add options section
        if hasattr(sim_config, '_options'):
            config_dict['options'] = sim_config._options.model_dump()
        
        # Preserve any other keys that might be in the original config
        for key in self.sim.config:
            if key not in ('control', 'material', 'options'):
                config_dict[key] = self.sim.config[key]
        
        self.sim.config = config_dict
    
    def update_attachment_constraints(self, attachment_constraints: list[Any]) -> None:
        """Update attachment constraints in simulation options.
        
        This method updates the attachment constraints in the simulation config
        using the class-based approach. It creates/updates SimulationOptions,
        updates the constraints, and then writes back to the config dict.
        
        Parameters
        ----------
        attachment_constraints : list[AttachmentConstraint]
            List of attachment constraint objects to inject into the config
        """
        from config import AttachmentConstraint
        
        # Get current SimConfig to access SimulationOptions
        sim_config = self.sim.get_sim_config()
        
        # Ensure all constraints are AttachmentConstraint objects
        constraints_objects = []
        for constraint in attachment_constraints:
            if isinstance(constraint, AttachmentConstraint):
                constraints_objects.append(constraint)
            elif isinstance(constraint, dict):
                # Convert dict to AttachmentConstraint
                constraints_objects.append(AttachmentConstraint(**constraint))
            else:
                # Try to convert using model_dump if available, then recreate
                if hasattr(constraint, 'model_dump'):
                    constraints_objects.append(AttachmentConstraint(**constraint.model_dump()))
                else:
                    raise ValueError(f"Cannot convert constraint to AttachmentConstraint: {type(constraint)}")
        
        # Update SimulationOptions with new constraints
        sim_config._options.attachment_constraints = constraints_objects
        sim_config._options.enable_attachment_constraint = True if constraints_objects else False
        
        # Update the config dict from the updated SimConfig
        self.update_sim_config(sim_config)

