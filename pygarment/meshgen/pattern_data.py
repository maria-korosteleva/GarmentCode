"""Data structures for passing in-memory pattern data between pipeline stages."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

from assets.bodies.body_params import BodyParameters
from pattern_definitions.body_definition import BodyDefinition
from config import AttachmentConstraint, PathCofig
from config.sim_config import SimConfig
from config.render_config import RenderConfig
from config.simulation_control import SimulationControl
from config.garment_properties import GarmentMaterialProperties
from config.simulation_options import SimulationOptions


@dataclass
class PatternData:
    """
    Container for in-memory pattern generation data.
    
    This class holds all the data structures needed to pass pattern information
    from the generation stage to the simulation stage without reading from disk.
    
    Attributes
    ----------
    piece : Any
        The garment piece/component object (e.g., WeonPants, WeonShirt).
        Must have a `name` attribute and `get_attachment_constraints()` method.
    body_params : BodyParameters
        Body parameters object for saving and metadata access.
    body_def : BodyDefinition
        Body definition object for garment creation and simulation.
    design : dict[str, Any]
        Design parameters dictionary.
    attachment_constraints : list[AttachmentConstraint]
        List of attachment constraints for simulation.
    paths : PathCofig
        Path configuration object containing all necessary file paths.
    """
    piece: Any
    body_params: BodyParameters
    body_def: BodyDefinition
    design: dict[str, Any]
    attachment_constraints: list[AttachmentConstraint]
    paths: PathCofig
    
    def __post_init__(self):
        """Validate required attributes."""
        if not hasattr(self.piece, 'name'):
            raise ValueError("piece must have a 'name' attribute")
        if not isinstance(self.attachment_constraints, list):
            raise ValueError("attachment_constraints must be a list")


@dataclass
class SimulationConfig:
    """
    Container for simulation and rendering configuration.
    
    This class holds all configuration needed for simulation using proper
    config classes instead of dictionaries.
    
    Attributes
    ----------
    sim_config : SimConfig
        Simulation configuration object.
    render_config : RenderConfig
        Render configuration object.
    data_folder : str
        Dataset folder name.
    """
    sim_config: SimConfig
    render_config: RenderConfig
    data_folder: str
    
    @classmethod
    def create_default(cls, data_folder: str) -> 'SimulationConfig':
        """Create SimulationConfig with default values.
        
        Uses Pydantic model defaults to create configuration without needing
        Properties or initialization helpers.
        
        Parameters
        ----------
        data_folder : str
            Dataset folder name.
            
        Returns
        -------
        SimulationConfig
            Initialized with default configuration.
        """
        # Create default config dicts using Pydantic models with defaults
        control_defaults = SimulationControl().model_dump()
        material_defaults = GarmentMaterialProperties().model_dump()
        options_defaults = SimulationOptions().model_dump()
        
        # Create sim config dict structure
        sim_config_dict = {
            'control': control_defaults,
            'material': material_defaults,
            'options': options_defaults,
            'max_meshgen_time': 20,  # Legacy parameter
        }
        
        # Create config objects
        sim_config = SimConfig(sim_config_dict)
        render_config = RenderConfig()  # Uses defaults from Pydantic model
        
        return cls(
            sim_config=sim_config,
            render_config=render_config,
            data_folder=data_folder
        )
    
    @classmethod
    def from_config_file(
        cls,
        config_path: Path,
        data_folder: str,
        default_config: Optional['SimulationConfig'] = None
    ) -> 'SimulationConfig':
        """Create SimulationConfig from a config file.
        
        Loads configuration from YAML/JSON file and merges with defaults.
        Uses Pydantic models for validation and default handling.
        
        Parameters
        ----------
        config_path : Path
            Path to the config YAML/JSON file.
        data_folder : str
            Dataset folder name.
        default_config : SimulationConfig, optional
            Default config to merge with. If None, uses create_default().
            
        Returns
        -------
        SimulationConfig
            Initialized from config file.
        """
        # Start with defaults
        if default_config is None:
            default_config = cls.create_default(data_folder)
        
        # Load config file
        with open(config_path, 'r') as f:
            file_data = yaml.safe_load(f)
        
        if not file_data:
            logger.warning(f"Config file {config_path} is empty, using defaults")
            return default_config
        
        # Extract sim and render configs from file
        file_sim_config = file_data.get('sim', {}).get('config', {})
        file_render_config = file_data.get('render', {}).get('config', {})
        
        # Merge with defaults: start with defaults, then update with file values
        default_sim_dict = default_config.sim_config._props.copy()
        
        # Deep merge control, material, options sections
        if 'control' in file_sim_config:
            default_sim_dict['control'] = {
                **default_sim_dict.get('control', {}),
                **file_sim_config['control']
            }
        if 'material' in file_sim_config:
            default_sim_dict['material'] = {
                **default_sim_dict.get('material', {}),
                **file_sim_config['material']
            }
        if 'options' in file_sim_config:
            default_sim_dict['options'] = {
                **default_sim_dict.get('options', {}),
                **file_sim_config['options']
            }
        
        # Merge top-level keys (like max_meshgen_time)
        for key, value in file_sim_config.items():
            if key not in ('control', 'material', 'options'):
                default_sim_dict[key] = value
        
        # Create config objects
        sim_config = SimConfig(default_sim_dict)
        
        # Merge render config
        if file_render_config:
            render_config = RenderConfig(**file_render_config)
        else:
            render_config = default_config.render_config
        
        return cls(
            sim_config=sim_config,
            render_config=render_config,
            data_folder=data_folder
        )

