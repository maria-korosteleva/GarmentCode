"""
    Fitting one sewing pattern design to a set of various body shapes
"""

from datetime import datetime
from pathlib import Path
from typing import Any
import yaml
import shutil 
import time
import argparse
import sys

from loguru import logger

# Custom
from pygarment.data_config import Properties
from garment_programs.garment_factory import GarmentFactory
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
        description='Fit sewing pattern design to various body shapes'
    )
    parser.add_argument('design_file', help='Path to design parameters file to be used to fit to the bodies', type=str)
    parser.add_argument('--batch_id', '-b', help='ID of a sampling batch', type=int, default=None) 
    parser.add_argument('--size', '-s', help='Number of body samples to generate', type=int, default=10)
    parser.add_argument('--name', '-n', help='Name of the dataset', type=str, default='design_fit')
    parser.add_argument('--replicate', '-re', help='Name of the dataset to re-generate. If set, other arguments are ignored', type=str, default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        set_log_level("DEBUG")
        logger.debug(f'Command line arguments: {args}')
    else:
        logger.info(f'Command line arguments: {args}')
    
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
            'objs': {'straight': f'meshes/{b_name}_straight.obj', 'apart': f'meshes/{b_name}_apart.obj'},
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
        with_3d=False, with_text=False, view_ids=False)

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


def generate(
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
        If the design specifies a garment type other than 'Pants'.
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
    
    # Validate garment type - only Pants is supported in this script
    garment_type = design.get('meta', {}).get('bottom', {}).get('v')
    if garment_type is not None and garment_type != 'Pants':
        raise ValueError(
            f"Unsupported garment type: {garment_type}. "
            f"Only 'Pants' is currently supported in pattern_fitter.py. "
            f"Please use pattern_data_sim.py for other garment types or set 'meta.bottom.v' to null."
        )

    # On default body
    default_body_params = BodyParameters(
        Path(sys_paths['bodies_default_path']) / (properties['body_default'] + '.yaml')
    )
    default_body_def = BodyDefinition(default_body_params.params)
    
    # Create garment using factory
    factory = GarmentFactory(default_body_def, design)
    piece_default = factory.create_pants()
    piece_default.name = properties['body_default']
    
    logger.info(f"Generating default body sample: {properties['body_default']}")
    _save_sample(piece_default, default_body_params, design, default_sample_data, verbose=verbose)
    
    # Generate samples
    num_samples = properties['size']
    max_available = len(body_options)
    if num_samples > max_available:
        logger.warning(f"Requested {num_samples} samples but only {max_available} available. Limiting to {max_available}.")
        num_samples = max_available
    
    logger.info(f'Generating {num_samples} body samples (out of {max_available} available)...')
    
    for i in range(num_samples):
        # Save properties periodically (every 10 samples or at start)
        if i % 10 == 0:
            properties.serialize(data_folder / 'dataset_properties.yaml')

        try:
            # On random body shape - for pants, use apart pose (straight=False)
            rand_body_params, rand_body_def = body_sample(
                i + properties['body_sample_start_id'],
                body_options,
                body_samples_path,
                straight=False)
            name = rand_body_params.params['body_sample']

            # Create garment using factory
            factory = GarmentFactory(rand_body_def, design)
            piece_shaped = factory.create_pants()
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


if __name__ == '__main__':
    system_props = Properties('./system.json')
    args = get_command_args()

    if args.replicate is not None:
        props = Properties(
            Path(system_props['datasets_path']) / args.replicate / 'dataset_properties.yaml',
            True)
    else:
        props = Properties()
        props.set_basic(
            design_file=args.design_file,
            body_default='mean_all',
            body_samples='5000_body_shapes_and_measures',
            body_sample_start_id=0,
            name=f'{args.name}_{args.size}' if not args.batch_id else f'{args.name}_{args.size}_{args.batch_id}',
            size=args.size,
            to_subfolders=True)
        props.set_section_config('generator')

    # Generate dataset
    try:
        default_path, body_sample_path = generate(
            system_props['datasets_path'], props, system_props, verbose=args.verbose)

        # Gather the pattern images separately
        gather_visuals(default_path, verbose=args.verbose)
        gather_visuals(body_sample_path, verbose=args.verbose)

        # At the end -- it takes some time to gather the info
        props.add_sys_info()  

        logger.success('Data generation completed!')
    except Exception as e:
        logger.error(f'Error during dataset generation: {e}')
        logger.exception("Exception details:")
        sys.exit(1)
