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
import time
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
from assets.bodies.body_params import BodyParameters
from pattern_definitions.body_definition import BodyDefinition

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


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
    
    args = parser.parse_args()
    
    # Validation
    if args.skip_generation and args.design:
        parser.error("--skip_generation can only be used with --data")
    if args.skip_simulation and args.data:
        parser.error("--skip_simulation can only be used with --design")
    
    # Set log level based on verbose flag
    if args.verbose:
        logger.remove()
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="DEBUG"
        )
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


def generate_dataset(
    path: str | Path,
    properties: Properties,
    sys_paths: Properties,
    verbose: bool = False
) -> tuple[Path, Path]:
    """Generate a synthetic dataset of patterns with given properties.
    
    Parameters:
    -----------
    path : str | Path
        Path to folder to put a new dataset into.
    properties : Properties
        An instance of DatasetProperties class with requested properties of the dataset.
    sys_paths : Properties
        System paths configuration Properties object (acts like a dictionary).
    verbose : bool, optional
        Whether to print verbose output. Default is False.
    
    Returns:
    --------
    tuple[Path, Path]
        Tuple containing (default_path, body_sample_path).
    
    Raises:
    -------
    ValueError
        If the design does not specify a valid garment type in 'meta.upper.v' or 'meta.bottom.v'.
    FileNotFoundError
        If required files or directories are not found.
    """
    path = Path(path)
    gen_stats = properties['generator']['stats']
    body_samples_path = Path(sys_paths['body_samples_path']) / properties['body_samples']
    body_options = _gather_body_options(body_samples_path)
    
    # Create data folder
    data_folder, default_path, body_sample_path = _create_data_folder(properties, path)
    default_sample_data = default_path / 'data'
    body_sample_data = body_sample_path / 'data'
    
    # Generate data
    start_time = time.time()
    
    # Load design
    with open(properties['design_file'], 'r') as f:
        design = yaml.safe_load(f)['design']
    
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
        use_straight_pose = True  # Composite garments typically include upper garments
        garment_type = 'Composite'
    elif upper_type:
        garment_type = upper_type  # 'Shirt' or 'FittedShirt'
        use_straight_pose = True  # Upper garments use straight pose
    elif bottom_type:
        garment_type = bottom_type  # 'Pants', 'SkirtCircle', 'AsymmSkirtCircle', etc.
        use_straight_pose = False  # Lower garments use apart pose
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
    else:
        piece_default = create_garment(garment_type, default_body_def, design)
    piece_default.name = properties['body_default']
    
    logger.info(f"Generating default body sample: {properties['body_default']}")
    _save_sample(piece_default, default_body_params, design, default_sample_data, verbose=verbose)
    
    # Generate samples - limit to requested number or available options, whichever is smaller
    max_available = len(body_options)
    requested_samples = properties['num_samples'] if 'num_samples' in properties else max_available
    num_samples = min(requested_samples, max_available) if requested_samples is not None else max_available
    
    logger.info(f'Generating {num_samples} body samples (out of {max_available} available)...')
    
    for i in range(num_samples):
        # Save properties periodically (every 10 samples or at start)
        if i % 10 == 0:
            properties.serialize(data_folder / 'dataset_properties.yaml')
        
        try:
            # On random body shape
            rand_body_params, rand_body_def = body_sample(
                i + properties['body_sample_start_id'],
                body_options,
                body_samples_path,
                straight=use_straight_pose
            )
            name = rand_body_params.params['body_sample']
            
            # Create garment using factory
            if is_composite:
                factory = GarmentFactory(rand_body_def, design)
                piece_shaped = factory.create_composite_garment()
            else:
                piece_shaped = create_garment(garment_type, rand_body_def, design)
            piece_shaped.name = name
            
            # Save samples
            _save_sample(piece_shaped, rand_body_params, design, body_sample_data, verbose=verbose)
            
            if (i + 1) % 10 == 0:
                logger.info(f'Generated {i + 1}/{num_samples} samples...')
                
        except KeyboardInterrupt:
            logger.warning("\nInterrupted by user. Exiting generation.")
            break
        except Exception as e:
            name = rand_body_params.params.get('body_sample', f'sample_{i}') if 'rand_body_params' in locals() else f'sample_{i}'
            logger.error(f'Processing for {name} failed: {e}')
            if verbose:
                logger.exception("Exception details:")
            continue
    
    elapsed = time.time() - start_time
    gen_stats['generation_time'] = f'{elapsed:.3f} s'
    
    # Save final properties
    properties.serialize(data_folder / 'dataset_properties.yaml')
    
    logger.info(f'Dataset generation completed in {elapsed:.3f} seconds')
    
    return default_path, body_sample_path


def gather_visuals(path: str | Path, verbose: bool = False) -> None:
    """Gather all pattern visualization images into a single directory.
    
    Parameters:
    -----------
    path : str | Path
        Base path to search for PNG pattern images.
    verbose : bool, optional
        Whether to print verbose output. Default is False.
    """
    vis_path = Path(path) / 'patterns_vis'
    vis_path.mkdir(parents=True, exist_ok=True)
    
    png_files = list(Path(path).rglob("*.png"))
    logger.info(f"Gathering {len(png_files)} pattern visualization images...")
    
    for p in png_files:
        try:
            shutil.copy(p, vis_path)
        except shutil.SameFileError:
            if verbose:
                logger.debug(f'File {p.name} already exists in destination')
            pass


def gather_renders(out_data_path: Path, verbose: bool = False) -> None:
    """Gather all render images into a single directory.
    
    Parameters:
    -----------
    out_data_path : Path
        Base path to search for render PNG images.
    verbose : bool, optional
        Whether to print verbose output. Default is False.
    """
    renders_path = out_data_path / 'renders'
    renders_path.mkdir(exist_ok=True)
    
    render_files = list(out_data_path.glob('**/*render*.png'))
    logger.info(f"Gathering {len(render_files)} render images...")
    
    for file in render_files:
        try:
            shutil.copy(str(file), str(renders_path))
        except shutil.SameFileError:
            if verbose:
                logger.debug(f'File {file} already exists in destination')
            pass


def run_simulation(
    dataset: str,
    system_config: Properties,
    command_args: argparse.Namespace
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
    
    Returns:
    --------
    bool
        True if simulation finished successfully, False otherwise.
    """
    datapath = Path(system_config['datasets_path']) / dataset
    init_dataset_file = datapath / 'dataset_properties.yaml'
    
    # Create dataset_file in correct folder (default_body or random_body)
    body_type = 'default_body' if command_args.default_body else 'random_body'
    datapath = datapath / body_type / 'data'  # Overwrite datapath to specific body type
    
    output_path = Path(system_config['datasets_sim']) / dataset / body_type
    output_path.mkdir(parents=True, exist_ok=True)
    dataset_file_body = output_path / f'dataset_properties_{body_type}.yaml'
    if not dataset_file_body.exists():
        shutil.copy(str(init_dataset_file), str(dataset_file_body))
    dataset_file = dataset_file_body
    
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
    
    # Main simulation loop - supports batching via num_samples=None for all samples
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
    
    # Try and resim fails once
    if finished:
        logger.info("Attempting to resimulate failed cases...")
        finished = sim.resim_fails(
            datapath,
            output_path,
            props,
            run_default_body=command_args.default_body,
            caching=command_args.caching
        )
    
    props.add_sys_info()  # Save system information
    props.serialize(dataset_file)
    
    # Gather renders
    gather_renders(output_path, verbose=command_args.verbose)
    
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
            props.set_section_config('generator')
        
        # Generate dataset
        try:
            default_path, body_sample_path = generate_dataset(
                system_config['datasets_path'],
                props,
                system_config,
                verbose=command_args.verbose
            )
            
            # Gather the pattern images separately
            gather_visuals(default_path, verbose=command_args.verbose)
            gather_visuals(body_sample_path, verbose=command_args.verbose)
            
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
        # Determine dataset name
        if dataset_name is None:
            if command_args.data:
                dataset_name = command_args.data
            else:
                logger.error('No dataset available for simulation')
                sys.exit(1)
        
        try:
            finished = run_simulation(dataset_name, system_config, command_args)
            
            if finished:
                logger.success('Dataset processing finished')
                sys.exit(0)
            else:
                logger.warning('Dataset processing not finished')
                sys.exit(1)
        except Exception as e:
            logger.error(f'Error during simulation: {e}')
            logger.exception("Exception details:")
            sys.exit(1)
    else:
        logger.info('Simulation skipped')
        sys.exit(0)
