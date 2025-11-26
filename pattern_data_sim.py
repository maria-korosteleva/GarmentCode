"""
    Unified script for pattern dataset generation and simulation with MayaPy standalone mode.
    
    This script combines pattern generation and simulation into a single workflow.
    
    How to use:
        * Fill out system.json with appropriate paths
        * Generate and simulate from design file:
          python pattern_data_sim.py --design <design_file.yaml> --name <dataset_name> [options]
    
    Note: This module can be executed in Maya (or by mayapy) for simulation.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

# Custom modules
import pygarment.data_config as data_config
import pygarment.meshgen.datasim_utils as sim
from pygarment.data_config import Properties
from garment_programs.garment_factory import create_garment, GarmentFactory
from config import AttachmentConstraint, PathCofig
from pygarment.meshgen.pattern_data import PatternData, SimulationConfig
from assets.bodies.body_params import BodyParameters
from pattern_definitions.body_definition import BodyDefinition
from log_config import set_log_level


def get_command_args() -> argparse.Namespace:
    """Parse command line arguments to control the run.
    
    Returns:
    --------
    argparse.Namespace
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='Generate pattern datasets and/or run simulations'
    )
    
    # Required input option
    parser.add_argument(
        '--design', '-d',
        help='Path to design parameters YAML file to generate dataset from',
        type=str,
        required=True
    )
    
    # Dataset generation options
    parser.add_argument(
        '--name', '-n',
        help='Name of the dataset (only used with --design)',
        type=str,
        default='design_fit'
    )
    parser.add_argument(
        '--batch_id', '-b',
        help='ID of a sampling batch (only used with --design)',
        type=int,
        default=None
    )
    # Simulation options
    parser.add_argument(
        '--config', '-c',
        help='Name of .json/.yaml file with desired simulation & rendering config',
        type=str,
        default="default_sim_props.yaml"
    )
    parser.add_argument(
        '--caching',
        action='store_true',
        help='Cache intermediate simulation results'
    )
    parser.add_argument(
        '--rewrite_config',
        action='store_true',
        help='Re-write simulation config even if it exists'
    )
    parser.add_argument(
        '--skip_simulation',
        action='store_true',
        help='Skip simulation, only generate dataset'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose output'
    )
    parser.add_argument(
        '--perfect-fit',
        action='store_true',
        help='Use perfect fit garment specification format (requires perfect fit spec YAML file)'
    )
    
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        set_log_level("DEBUG")
        logger.debug(f'Command line arguments: {args}')
    
    return args


def _create_data_folder(properties: Properties, path: Path = Path('')) -> tuple[Path, Path]:
    """Create a new directory to put dataset in and generate appropriate name.
    
    Parameters:
    -----------
    properties : Properties
        Dataset properties object that will be updated with the data folder name.
    path : Path, optional
        Base path where the dataset folder will be created. Default is current directory.
    
    Returns:
    --------
    tuple[Path, Path]
        Tuple containing:
        - path_with_dataset: Full path to the created dataset folder
        - default_folder: Path to the default_body subfolder
    """
    if 'data_folder' in properties:
        # Regenerating from existing data
        properties['name'] = properties['data_folder'] + '_regen'
        data_folder = properties['name']
    else:
        data_folder = properties['name']
    
    data_folder = f"{data_folder}_{datetime.now().strftime('%y%m%d-%H-%M-%S')}"
    properties['data_folder'] = data_folder
    path_with_dataset = path / data_folder
    path_with_dataset.mkdir(parents=True)
    
    default_folder = path_with_dataset / 'default_body'
    default_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created dataset folder: {data_folder}")
    logger.info("Using default body configuration (default_body)")
    
    return path_with_dataset, default_folder


def body_sample(
    idx: int,
    bodies: list[dict[str, Any]],
    path: Path,
    straight: bool = True
) -> tuple[BodyParameters, BodyDefinition]:
    """Sample a body from the available body options.
    
    Parameters:
    -----------
    idx : int
        Index of the body to sample.
    bodies : list[dict[str, Any]]
        List of body information dictionaries.
    path : Path
        Base path to the body samples directory.
    straight : bool, optional
        Whether to use straight or apart pose. Default is True.
    
    Returns:
    --------
    tuple[BodyParameters, BodyDefinition]
        Tuple containing:
        - BodyParameters: For saving and metadata access
        - BodyDefinition: For garment creation
    """
    body_i = bodies[idx]
    
    mes_file = body_i['mes']
    obj_file = body_i['objs']['straight'] if straight else body_i['objs']['apart']
    
    body_params = BodyParameters(path / mes_file)
    body_params.params['body_sample'] = (path / obj_file).stem
    
    # Convert to BodyDefinition for garment creation
    body_def = BodyDefinition(body_params.params)
    
    return body_params, body_def


def _save_sample(
    piece: Any,
    body: BodyParameters,
    new_design: dict[str, Any],
    folder: Path,
    verbose: bool = False
) -> None:
    """Save a garment pattern sample to disk.
    
    Parameters:
    -----------
    piece : Any
        The garment piece/component to save (must have assembly() method and name attribute).
    body : BodyParameters
        Body parameters object to save alongside the pattern.
    new_design : dict[str, Any]
        Design parameters dictionary to save.
    folder : Path
        Directory path where the sample will be saved.
    verbose : bool, optional
        Whether to print verbose output. Default is False.
    """
    pattern = piece.assembly()
    # Save as json file
    folder = pattern.serialize(
        folder,
        tag='',
        to_subfolder=True,
        with_3d=False,
        with_text=False,
        view_ids=False
    )
    
    body.save(folder)
    with open(Path(folder) / 'design_params.yaml', 'w') as f:
        yaml.dump(
            {'design': new_design},
            f,
            default_flow_style=False,
            sort_keys=False
        )
    
    if verbose:
        logger.debug(f'Saved {piece.name}')


def generate_sewing_pattern(
    path: str | Path,
    properties: Properties,
    sys_paths: Properties,
    verbose: bool = False
) -> tuple[Path, dict[str, PatternData]]:
    """Generate a pattern sample with given properties.
    
    Parameters:
    -----------
    path : str | Path
        Path to folder to put a new dataset into.
    properties : Properties
        A Properties object with requested properties of the dataset.
    sys_paths : Properties
        System paths configuration Properties object (acts like a dictionary).
    verbose : bool, optional
        Whether to print verbose output. Default is False.
    
    Returns:
    --------
    tuple[Path, dict[str, PatternData]]
        Tuple containing:
        - default_path: Path to default body data folder
        - default_pattern_data: Dict mapping pattern names to PatternData objects
    
    Raises:
    -------
    ValueError
        If the design does not specify a valid garment type in 'meta.upper.v' or 'meta.bottom.v'.
    FileNotFoundError
        If required files or directories are not found.
    """
    path = Path(path)
    
    # Create data folder
    _, default_path = _create_data_folder(properties, path)
    default_sample_data = default_path / 'data'
    
    # Store pattern data in memory (for direct passing to simulation)
    default_pattern_data: dict[str, PatternData] = {}
    
    # Load design file
    with open(properties['design_file'], 'r') as f:
        loaded_data = yaml.safe_load(f)
    
    # Check if perfect fit flag is set or if file is perfect fit spec format
    perfect_fit_flag = properties['perfect_fit'] if 'perfect_fit' in properties else False
    use_perfect_fit = perfect_fit_flag or ('garment_type' in loaded_data and 'design' not in loaded_data)
    
    if use_perfect_fit:
        # Perfect fit spec format - use directly without conversion
        logger.info('Using perfect fit garment specification')
        perfect_fit_spec = loaded_data
        garment_type = perfect_fit_spec.get('garment_type', 'Pants')
        # Set garment type for later use
        upper_type = None
        bottom_type = garment_type
        wb_type = None
        design = perfect_fit_spec  # Use perfect fit spec directly
    else:
        # Regular design file format
        design = loaded_data.get('design', loaded_data)  # Support both {'design': {...}} and direct {...}
        # Determine garment type from design (check both upper and bottom)
        upper_type = design.get('meta', {}).get('upper', {}).get('v')
        bottom_type = design.get('meta', {}).get('bottom', {}).get('v')
        wb_type = design.get('meta', {}).get('wb', {}).get('v')
    
    # Check if this is a composite garment (has both upper and lower, or waistband)
    is_composite = (upper_type and bottom_type) or (upper_type and wb_type) or (bottom_type and wb_type)
    
    # Determine which garment to create and appropriate pose
    if is_composite:
        # Composite garment (dress/jumpsuit) - use factory's composite method
        logger.info(f'Detected composite garment: upper={upper_type}, bottom={bottom_type}, wb={wb_type}')
        garment_type = 'Composite'
    elif upper_type:
        garment_type = upper_type  # 'Shirt' or 'FittedShirt'
    elif bottom_type:
        garment_type = bottom_type  # 'Pants', 'SkirtCircle', 'AsymmSkirtCircle', etc.
    else:
        raise ValueError(
            "Design must specify either 'meta.upper.v' or 'meta.bottom.v' to determine garment type. "
            f"Found: upper={upper_type}, bottom={bottom_type}"
        )
    
    if not is_composite:
        logger.info(f'Detected garment type: {garment_type}')
    
    # On default body
    default_body_params = BodyParameters(
        Path(sys_paths['bodies_default_path']) / (properties['body_default'] + '.yaml')
    )
    default_body_def = BodyDefinition(default_body_params.params)
    
    # Create garment using factory
    if is_composite:
        factory = GarmentFactory(default_body_def, design)
        piece_default = factory.create_composite_garment()
        # Composite garments don't have constraints yet, use empty list
        constraints_default: list[AttachmentConstraint] = []
    elif use_perfect_fit:
        # Use perfect fit factory method
        factory = GarmentFactory(default_body_def, design)
        piece_default = factory.create_pants_perfect_fit()
        constraints_default = piece_default.get_attachment_constraints()  # type: ignore[attr-defined]
    else:
        piece_default, constraints_default = create_garment(garment_type, default_body_def, design)
    piece_default.name = properties['body_default']
    
    logger.info(f"Generating default body sample: {properties['body_default']}")
    _save_sample(piece_default, default_body_params, design, default_sample_data, verbose=verbose)
    
    # Create PathCofig for default body (will be used in simulation)
    # Determine output path for simulation
    datasets_sim_path = Path(sys_paths['datasets_sim'] if 'datasets_sim' in sys_paths else path / 'datasets_sim')
    output_path = datasets_sim_path / properties['data_folder'] / 'default_body'
    output_path.mkdir(parents=True, exist_ok=True)
    
    paths_config_default = PathCofig(
        in_element_path=default_sample_data / piece_default.name,
        out_path=output_path,
        in_name=piece_default.name,
        body_name=properties['body_default'],
        samples_name='',  # Not using body samples
        default_body=True,
        bodies_default_path=sys_paths['bodies_default_path'],
        body_samples_path=None
    )
    
    # Store default body pattern data in memory
    default_pattern_data[piece_default.name] = PatternData(
        piece=piece_default,
        body_params=default_body_params,
        body_def=default_body_def,
        design=design,
        attachment_constraints=constraints_default,
        paths=paths_config_default
    )
    
    return default_path, default_pattern_data


def run_simulation(
    dataset: str,
    system_config: Properties,
    command_args: argparse.Namespace,
    pattern_data: dict[str, PatternData],
    sim_config: SimulationConfig | None = None
) -> bool:
    """Run simulation on an existing dataset.
    
    Parameters:
    -----------
    dataset : str
        Name of the dataset folder to simulate.
    system_config : Properties
        System configuration properties.
    command_args : argparse.Namespace
        Parsed command line arguments.
    pattern_data : dict[str, PatternData]
        In-memory pattern data dict mapping pattern names to PatternData objects.
        Required for simulation.
    sim_config : SimulationConfig | None, optional
        Optional simulation configuration object. If provided, will be used instead of
        creating Properties from scratch. If None, will create from config file.
    
    Returns:
    --------
    bool
        True if simulation finished successfully, False otherwise.
    """
    body_type = 'default_body'
    logger.info("Using default body configuration (default_body)")
    output_path = Path(system_config['datasets_sim']) / dataset / body_type
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Use in-memory pattern data (required)
    if pattern_data is None:
        logger.error('Pattern data is required. Cannot run simulation without pattern data.')
        return False
    
    logger.info(f"Using in-memory pattern data for {len(pattern_data)} patterns")
    
    # Use provided sim_config or create from scratch
    if sim_config is None:
        if command_args.config is not None:
            config_path = Path(system_config['sim_configs_path']) / command_args.config
            logger.info(f"Loading simulation config from: {config_path}")
            sim_config_obj = SimulationConfig.from_config_file(config_path, dataset)
        else:
            sim_config_obj = SimulationConfig.create_default(dataset)
            logger.info(f"Created default simulation config for dataset: {dataset}")
    else:
        sim_config_obj = sim_config
    
    # Main simulation loop
    logger.info(f"Starting simulation for dataset: {dataset} (body_type: {body_type})")
    finished = sim.batch_sim_with_data(
        pattern_data,
        sim_config_obj,
        run_default_body=True,
        num_samples=1,
        caching=command_args.caching,
        force_restart=False
    )
    
    return finished


if __name__ == "__main__":
    command_args = get_command_args()
    system_config = data_config.Properties('./system.json')
    
    # Step 1: Generate dataset from design file
    logger.info(f'Generating dataset from design file: {command_args.design}')
    
    # Set up properties for generation
    props = Properties()
    props.set_basic(
        design_file=command_args.design,
        body_default='mean_all',
        name=command_args.name if not command_args.batch_id else f'{command_args.name}_{command_args.batch_id}',
        to_subfolders=True
    )
    props['perfect_fit'] = command_args.perfect_fit  # Store perfect fit flag
    props.set_section_config('generator')
    
    # Get patterns_path from system config, default to './patterns' if not set
    patterns_path = Path(system_config['patterns_path'] if 'patterns_path' in system_config else './patterns')
    
    # Generate dataset
    try:
        default_path, default_pattern_data = generate_sewing_pattern(
            patterns_path,
            props,
            system_config,
            verbose=command_args.verbose
        )
        
        # At the end -- it takes some time to gather the info
        props.add_sys_info()
        
        # Get the dataset name from properties
        dataset_name = props['data_folder']
        
        logger.info(f'Data generation completed! Dataset: {dataset_name}')
            
    except Exception as e:
        logger.error(f'Error during dataset generation: {e}')
        logger.exception("Exception details:")
        sys.exit(1)
    
    # Step 2: Run simulation if not skipped
    if not command_args.skip_simulation:
        # Create SimulationConfig from properties (for in-memory use)
        if command_args.config is not None:
            config_path = Path(system_config['sim_configs_path']) / command_args.config
            logger.info(f"Loading simulation config from: {config_path}")
            sim_config_for_sim = SimulationConfig.from_config_file(config_path, dataset_name)
        else:
            sim_config_for_sim = SimulationConfig.create_default(dataset_name)
        
        finished = run_simulation(dataset_name, system_config, command_args, default_pattern_data, sim_config_for_sim)
    else:
        logger.info('Simulation skipped')
        sys.exit(0)
