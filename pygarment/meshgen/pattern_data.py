"""Data structures for passing in-memory pattern data between pipeline stages."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from assets.bodies.body_params import BodyParameters
from pattern_definitions.body_definition import BodyDefinition
from config import AttachmentConstraint, PathCofig
from config.sim_config import SimConfig
from config.render_config import RenderConfig


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
    frozen : bool, optional
        Whether the dataset is frozen (processing complete). Default is False.
    """
    sim_config: SimConfig
    render_config: RenderConfig
    data_folder: str
    frozen: bool = False
    
    @classmethod
    def create_default(cls, data_folder: str) -> 'SimulationConfig':
        """
        Create SimulationConfig with default values.
        
        Parameters
        ----------
        data_folder : str
            Dataset folder name.
            
        Returns
        -------
        SimulationConfig
            Initialized with default configuration.
        """
        import pygarment.meshgen.datasim_utils as sim_utils
        from pygarment.data_config import Properties
        
        # Create Properties to use init_sim_props helper
        props = Properties()
        props.set_basic(data_folder=data_folder, name=data_folder)
        sim_utils.init_sim_props(props, batch_run=True, force_restart=False)
        
        # Extract config dicts
        sim_config_dict = props['sim']['config']
        render_config_dict = props['render']['config']
        
        # Create config objects
        sim_config = SimConfig(sim_config_dict)
        render_config = RenderConfig(**render_config_dict)
        
        return cls(
            sim_config=sim_config,
            render_config=render_config,
            data_folder=data_folder,
            frozen=False
        )
    
    @classmethod
    def from_config_file(
        cls,
        config_path: Path,
        data_folder: str,
        default_config: Optional['SimulationConfig'] = None
    ) -> 'SimulationConfig':
        """
        Create SimulationConfig from a config file.
        
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
        import pygarment.meshgen.datasim_utils as sim_utils
        from pygarment.data_config import Properties
        
        # Start with defaults
        if default_config is None:
            default_config = cls.create_default(data_folder)
        
        # Load config file
        props = Properties()
        props.set_basic(data_folder=data_folder, name=data_folder)
        sim_utils.init_sim_props(props, batch_run=True, force_restart=False)
        props.merge(str(config_path), re_write=True)
        
        # Extract config dicts
        sim_config_dict = props['sim']['config']
        render_config_dict = props['render']['config']
        
        # Create config objects
        sim_config = SimConfig(sim_config_dict)
        render_config = RenderConfig(**render_config_dict)
        
        return cls(
            sim_config=sim_config,
            render_config=render_config,
            data_folder=data_folder,
            frozen=props['frozen'] if 'frozen' in props else False
        )

