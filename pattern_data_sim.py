"""
    Unified script for pattern dataset generation and simulation with MayaPy standalone mode.
    
    This script combines pattern generation (from pattern_fitter.py) and simulation
    (from pattern_data_sim.py) into a single workflow.
    
    How to use:
        * Fill out system.json with appropriate paths
        * Generate and simulate from design file:
          python pattern_data_sim.py --design <design_file.yaml> --name <dataset_name> [options]
        * Simulate existing dataset:
          python pattern_data_sim.py --data <dataset_folder_name> [options]
    
    Note: This module can be executed in Maya (or by mayapy) for simulation.
"""

import argparse
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--design', '-d',
        help='Path to design parameters YAML file to generate dataset from',
        type=str
    )
    input_group.add_argument(
        '--data',
        help='Name of existing dataset folder to simulate',
        type=str
    )
    
    # Dataset generation options (only used with --design)
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
    parser.add_argument(
        '--replicate', '-re',
        help='Name of the dataset to re-generate. If set, other arguments are ignored',
        type=str,
        default=None
    )
    parser.add_argument(
        '--num_samples',
        help='Number of body samples to generate (default: 1). Use None for all samples.',
        type=int,
        default=1
    )
    
    # Simulation options
    parser.add_argument(
        '--config', '-c',
        help='Name of .json/.yaml file with desired simulation & rendering config',
        type=str,
        default=None
    )
    parser.add_argument(
        '--default_body',
        action='store_true',
        help='Run dataset on default body only'
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
        '--skip_generation',
        action='store_true',
        help='Skip dataset generation, only run simulation (requires --data)'
    )
    parser.add_argument(
        '--skip_simulation',
        action='store_true',
        help='Skip simulation, only generate dataset (requires --design)'
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
    
    # Validation
    if args.skip_generation and args.design:
        parser.error("--skip_generation can only be used with --data")
    if args.skip_simulation and args.data:
        parser.error("--skip_simulation can only be used with --design")
    
    # Set log level based on verbose flag
    if args.verbose:
        set_log_level("DEBUG")
        logger.debug(f'Command line arguments: {args}')
    
    return args


def _create_data_folder(properties: Properties, path: Path = Path('')) -> tuple[Path, Path, Path]:
    """Create a new directory to put dataset in and generate appropriate name.
    
    Parameters:
    -----------
    properties : Properties
        Dataset properties object that will be updated with the data folder name.
    path : Path, optional
        Base path where the dataset folder will be created. Default is current directory.
    
    Returns:
    --------
    tuple[Path, Path, Path]
        Tuple containing:
        - path_with_dataset: Full path to the created dataset folder
        - default_folder: Path to the default_body subfolder
        - body_folder: Path to the random_body subfolder
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
    body_folder = path_with_dataset / 'random_body'
    
    default_folder.mkdir(parents=True, exist_ok=True)
    body_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created dataset folder: {data_folder}")
    
    return path_with_dataset, default_folder, body_folder


def _gather_body_options(body_path: Path) -> list[dict[str, Any]]:
    """Gather available body options from the body samples directory.
    
    Parameters:
    -----------
    body_path : Path
        Path to the body samples directory containing measurements and meshes.
    
    Returns:
    --------
    list[dict[str, Any]]
        List of body information dictionaries, each containing:
        - 'objs': Dictionary with 'straight' and 'apart' mesh file paths
        - 'mes': Path to the measurements YAML file
    
    Raises:
    -------
    FileNotFoundError
        If the measurements directory does not exist.
    """
    measurements_path = body_path / 'measurements'
    
    bodies: list[dict[str, Any]] = []
    if not measurements_path.exists() or not measurements_path.is_dir():
        raise FileNotFoundError(f"Measurements directory not found at {measurements_path}")
    
    for file in measurements_path.glob('*.yaml'):
        # Get name
        b_name = file.stem.split('_')[0]
        body_info: dict[str, Any] = {
            'objs': {
                'straight': f'meshes/{b_name}_straight.obj',
                'apart': f'meshes/{b_name}_apart.obj'
            },
            'mes': f'measurements/{file.name}'
        }
        bodies.append(body_info)
    
    logger.debug(f"Found {len(bodies)} body options in {body_path}")
    return bodies


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
) -> tuple[Path, Path, dict[str, PatternData], dict[str, PatternData]]:
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
    tuple[Path, Path, dict[str, PatternData], dict[str, PatternData]]
        Tuple containing:
        - default_path: Path to default body data folder
        - body_sample_path: Path to body sample data folder
        - default_pattern_data: Dict mapping pattern names to PatternData objects
        - body_sample_pattern_data: Dict mapping pattern names to PatternData objects
    
    Raises:
    -------
    ValueError
        If the design does not specify a valid garment type in 'meta.upper.v' or 'meta.bottom.v'.
    FileNotFoundError
        If required files or directories are not found.
    """
    path = Path(path)
    body_samples_path = Path(sys_paths['body_samples_path']) / properties['body_samples']
    body_options = _gather_body_options(body_samples_path)
    
    # Create data folder
    _, default_path, body_sample_path = _create_data_folder(properties, path)
    default_sample_data = default_path / 'data'
    
    # Store pattern data in memory (for direct passing to simulation)
    default_pattern_data: dict[str, PatternData] = {}
    body_sample_pattern_data: dict[str, PatternData] = {}
    
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
        samples_name=properties['body_samples'] if 'body_samples' in properties else '',  # type: ignore[assignment]
        default_body=True,
        bodies_default_path=sys_paths['bodies_default_path'],
        body_samples_path=sys_paths['body_samples_path'] if 'body_samples_path' in sys_paths else None
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
    
    # Generate samples - limit to requested number or available options, whichever is smaller
    max_available = len(body_options)
    requested_samples = properties['num_samples'] if 'num_samples' in properties else max_available
    num_samples = min(requested_samples, max_available) if requested_samples is not None else max_available
    
    logger.info(f'Generating {num_samples} body samples (out of {max_available} available)...')

    return default_path, body_sample_path, default_pattern_data, body_sample_pattern_data


def run_simulation(
    dataset: str,
    system_config: Properties,
    command_args: argparse.Namespace,
    pattern_data: dict[str, PatternData] | None = None,
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
    pattern_data : dict[str, PatternData] | None, optional
        Optional in-memory pattern data dict mapping pattern names to PatternData objects.
        If provided, this data will be used directly instead of reading from disk.
        If None, data will be read from disk (backward compatible).
    sim_config : SimulationConfig | None, optional
        Optional simulation configuration object. If provided, will be used instead of
        creating Properties from scratch. If None, will create from config file.
    
    Returns:
    --------
    bool
        True if simulation finished successfully, False otherwise.
    """
    body_type = 'default_body' if command_args.default_body else 'random_body'
    datapath = Path(system_config['datasets_path']) / dataset / body_type / 'data'
    output_path = Path(system_config['datasets_sim']) / dataset / body_type
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Use in-memory data if available, otherwise read from disk
    if pattern_data is not None:
        logger.info(f"Using in-memory pattern data for {len(pattern_data)} patterns")
        
        # Use provided sim_config or create from scratch
        if sim_config is None:
            if command_args.config is not None:
                config_path = Path(system_config['sim_configs_path']) / command_args.config
                logger.info(f"Loading simulation config from: {config_path}")
                sim_config_obj = SimulationConfig.from_config_file(config_path, dataset)
            else:
                sim_config_obj = SimulationConfig.create_default(dataset)
        else:
            sim_config_obj = sim_config
        
        # Main simulation loop
        logger.info(f"Starting simulation for dataset: {dataset} (body_type: {body_type})")
        finished = sim.batch_sim_with_data(
            pattern_data,
            sim_config_obj,
            run_default_body=command_args.default_body,
            num_samples=None,
            caching=command_args.caching,
            force_restart=False
        )
    else:
        logger.info("Reading pattern data from disk (backward compatible mode)")
        # Backward compatibility: use file-based approach
        init_dataset_file = Path(system_config['datasets_path']) / dataset / 'dataset_properties.yaml'
        dataset_file_body = output_path / f'dataset_properties_{body_type}.yaml'
        if not dataset_file_body.exists():
            if init_dataset_file.exists():
                shutil.copy(str(init_dataset_file), str(dataset_file_body))
            else:
                # Create from scratch if file doesn't exist
                props = data_config.Properties()
                props.set_basic(data_folder=dataset)
                import pygarment.meshgen.datasim_utils as sim_utils
                sim_utils.init_sim_props(props, batch_run=True, force_restart=False)
                if command_args.config is not None:
                    config_path = Path(system_config['sim_configs_path']) / command_args.config
                    logger.info(f"Loading simulation config from: {config_path}")
                    props.merge(config_path, re_write=command_args.rewrite_config)
                props.serialize(dataset_file_body)
        
        props = data_config.Properties(dataset_file_body)
        if 'frozen' in props and props['frozen']:
            logger.warning('Dataset is frozen, processing is skipped')
            return False
        
        # Define sim props
        props.set_basic(data_folder=dataset)
        if command_args.config is not None:
            config_path = Path(system_config['sim_configs_path']) / command_args.config
            logger.info(f"Loading simulation config from: {config_path}")
            props.merge(
                config_path,
                re_write=command_args.rewrite_config
            )
        
        # Main simulation loop
        logger.info(f"Starting simulation for dataset: {dataset} (body_type: {body_type})")
        finished = sim.batch_sim(
            datapath,
            output_path,
            props,
            run_default_body=command_args.default_body,
            num_samples=None,  # None = process all samples, can be set to a number for batching
            caching=command_args.caching,
            force_restart=False
        )
    
    return finished


if __name__ == "__main__":
    command_args = get_command_args()
    system_config = data_config.Properties('./system.json')
    
    dataset_name: Optional[str] = None
    
    # Step 1: Generate dataset if design file is provided
    if command_args.design and not command_args.skip_generation:
        logger.info(f'Generating dataset from design file: {command_args.design}')
        
        # Set up properties for generation
        if command_args.replicate is not None:
            props = Properties(
                Path(system_config['datasets_path']) / command_args.replicate / 'dataset_properties.yaml',
                True
            )
        else:
            props = Properties()
            props.set_basic(
                design_file=command_args.design,
                body_default='mean_all',
                body_samples='5000_body_shapes_and_measures',
                body_sample_start_id=0,
                name=command_args.name if not command_args.batch_id else f'{command_args.name}_{command_args.batch_id}',
                to_subfolders=True
            )
            props['num_samples'] = command_args.num_samples
            props['perfect_fit'] = command_args.perfect_fit  # Store perfect fit flag
            props.set_section_config('generator')
        
        # Generate dataset
        try:
            default_path, body_sample_path, default_pattern_data, body_sample_pattern_data = generate_sewing_pattern(
                system_config['datasets_path'],
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
    
    # Store pattern data for simulation stage (if generation was run)
    pattern_data_for_sim: dict[str, PatternData] | None = None
    sim_config_for_sim: SimulationConfig | None = None
    if command_args.design is not None:
        # Generation was run, use the appropriate pattern data
        pattern_data_for_sim = default_pattern_data if command_args.default_body else body_sample_pattern_data
        
        # Create SimulationConfig from properties (for in-memory use)
        if dataset_name is not None:
            if command_args.config is not None:
                config_path = Path(system_config['sim_configs_path']) / command_args.config
                logger.info(f"Loading simulation config from: {config_path}")
                sim_config_for_sim = SimulationConfig.from_config_file(config_path, dataset_name)
            else:
                sim_config_for_sim = SimulationConfig.create_default(dataset_name)
        else:
            sim_config_for_sim = None
    
    # Step 2: Run simulation if not skipped
    if not command_args.skip_simulation:
        # Determine dataset name
        if dataset_name is None:
            if command_args.data:
                dataset_name = command_args.data
            else:
                logger.error('No dataset available for simulation')
                sys.exit(1)
        
        finished = run_simulation(dataset_name, system_config, command_args, pattern_data_for_sim, sim_config_for_sim)
    else:
        logger.info('Simulation skipped')
        sys.exit(0)
