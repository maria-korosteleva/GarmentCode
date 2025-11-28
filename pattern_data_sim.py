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
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

# Custom modules
import pygarment.meshgen.datasim_utils as sim
from pygarment.meshgen.cli_pattern_config import CLIPatternConfig
from garment_programs.garment_factory import create_garment, GarmentFactory
from pygarment.meshgen.pattern_data import PatternData, SimulationConfig
from assets.bodies.body_params import BodyParameters

from config import AttachmentConstraint, PathCofig
from pattern_definitions.body_definition import BodyDefinition
from log_config import set_log_level


def get_command_args() -> argparse.Namespace:
    """Parse command line arguments to control the run.
    
    Returns
    -------
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

    parser.add_argument(
        '--output',
        help='Output directory for logs',
        type=str,
        default="./Logs/"
    )
    parser.add_argument(
        '--patterns_path',
        help='Path to output patterns',
        type=str,
        default="sewing_pattern"
    )
    parser.add_argument(
        '--datasets_sim',
        help='Path to output simulations',
        type=str,
        default="simulation"
    )
    parser.add_argument(
        '--sim_configs_path',
        help='Path to simulation configs directory',
        type=str,
        default="./assets/Sim_props"
    )
    parser.add_argument(
        '--bodies_default_path',
        help='Path to default bodies directory',
        type=str,
        default="./assets/bodies/smplx_sample"
    )
    parser.add_argument(
        '--body_samples_path',
        help='Path to body samples directory',
        type=str,
        default=""
    )
    parser.add_argument(
        "--body_name",
        help='The name of the body selected from --bodies_default_path',
        type=str,
        default="female_00018_default_pose"
    )
    
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        set_log_level("DEBUG")
        logger.debug(f'Command line arguments: {args}')
    
    return args


def _create_data_folder(config: CLIPatternConfig, path: Path = Path('')) -> tuple[Path, Path]:
    """Create a new directory for pattern output and generate appropriate name.
    
    Parameters
    ----------
    config : CLIPatternConfig
        Pattern configuration object that will be updated with the output folder name.
    path : Path, optional
        Base path where the output folder will be created. Default is current directory.
    
    Returns
    -------
    tuple[Path, Path]
        Tuple containing:
        - path_with_output: Full path to the created output folder
        - default_folder: Path to the default_body subfolder
    """
    regenerate = config.output_folder is not None
    output_folder = config.generate_output_folder_name(regenerate=regenerate)
    
    path_with_output = path / output_folder
    path_with_output.mkdir(parents=True, exist_ok=True)
    
    default_folder = path_with_output / 'default_body'
    default_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created pattern output folder: {output_folder}")
    logger.info("Using default body configuration (default_body)")
    
    return path_with_output, default_folder


def body_sample(
    idx: int,
    bodies: list[dict[str, Any]],
    path: Path,
    straight: bool = True
) -> tuple[BodyParameters, BodyDefinition]:
    """Sample a body from the available body options.
    
    Parameters
    ----------
    idx : int
        Index of the body to sample.
    bodies : list[dict[str, Any]]
        List of body information dictionaries.
    path : Path
        Base path to the body samples directory.
    straight : bool, optional
        Whether to use straight or apart pose. Default is True.
    
    Returns
    -------
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
    
    Parameters
    ----------
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
    config: CLIPatternConfig,
    bodies_default_path: str,
    datasets_sim: str,
    verbose: bool = False
) -> tuple[Path, dict[str, PatternData]]:
    """Generate a pattern sample with given configuration.

    Parameters
    ----------
    path : str | Path
        Path to folder to put pattern output into.
    config : CLIPatternConfig
        Pattern configuration object with requested properties for pattern generation.
    bodies_default_path : str
        Path to the default bodies directory.
    datasets_sim : str
        Path to the datasets simulation directory.
    verbose : bool, optional
        Whether to print verbose output. Default is False.

    Returns
    -------
    tuple[Path, dict[str, PatternData]]
        Tuple containing:
        - default_path: Path to default body pattern folder
        - default_pattern_data: Dict mapping pattern names to PatternData objects

    Raises
    ------
    ValueError
        If the design does not specify a valid garment type in 'meta.upper.v' or 'meta.bottom.v'.
    FileNotFoundError
        If required files or directories are not found.
    """
    path = Path(path)

    # Create output folder for patterns
    _, default_path = _create_data_folder(config, path)
    default_sample_data = default_path / 'data'

    # Store pattern data in memory (for direct passing to simulation)
    default_pattern_data: dict[str, PatternData] = {}

    # Load design file
    with open(config.design_file, 'r') as f:
        loaded_data = yaml.safe_load(f)

    # Detect if this is a perfect fit spec format
    is_perfect_fit_format = 'garment_type' in loaded_data and 'design' not in loaded_data
    use_perfect_fit = config.perfect_fit or is_perfect_fit_format

    # Extract garment type and relevant design
    if use_perfect_fit:
        logger.info('Using perfect fit garment specification')
        design = loaded_data
        garment_type = design.get('garment_type', 'Pants')
        upper_type, bottom_type, wb_type = None, garment_type, None
    else:
        # Support both {'design': {...}} and direct {...}
        design = loaded_data.get('design', loaded_data)
        meta = design.get('meta', {})
        upper_type = meta.get('upper', {}).get('v')
        bottom_type = meta.get('bottom', {}).get('v')
        wb_type = meta.get('wb', {}).get('v')
        garment_type = None  # will be determined below

    # On default body
    default_body_params = BodyParameters(
        Path(bodies_default_path) / f"{config.body_name}.yaml"
    )
    default_body_def = BodyDefinition(default_body_params.params)

    # Determine garment type and composite status
    is_composite = any([
        upper_type and bottom_type,
        upper_type and wb_type,
        bottom_type and wb_type
    ])

    if not use_perfect_fit:
        if is_composite:
            logger.info(f'Detected composite garment: upper={upper_type}, bottom={bottom_type}, wb={wb_type}')
            garment_type = 'Composite'
        elif upper_type:
            garment_type = upper_type
        elif bottom_type:
            garment_type = bottom_type
        else:
            raise ValueError(
                "Design must specify either 'meta.upper.v' or 'meta.bottom.v' to determine garment type. "
                f"Found: upper={upper_type}, bottom={bottom_type}"
            )

    if not is_composite and not use_perfect_fit:
        logger.info(f'Detected garment type: {garment_type}')

    # Create garment using factory
    if is_composite:
        factory = GarmentFactory(default_body_def, design)
        piece_default = factory.create_composite_garment()
        constraints_default: list[AttachmentConstraint] = []
    elif use_perfect_fit:
        factory = GarmentFactory(default_body_def, design)
        piece_default = factory.create_pants_perfect_fit()
        constraints_default = piece_default.get_attachment_constraints()  # type: ignore[attr-defined]
    else:
        piece_default, constraints_default = create_garment(garment_type, default_body_def, design)

    piece_default.name = config.body_name
    logger.info(f"Generating default body sample: {config.body_name}")
    _save_sample(piece_default, default_body_params, design, default_sample_data, verbose=verbose)

    # Create PathCofig for default body (will be used in simulation)
    datasets_sim_path = Path(datasets_sim)
    if config.output_folder is None:
        raise ValueError("output_folder must be set before creating PathCofig")
    output_path = datasets_sim_path / config.output_folder / 'default_body'
    output_path.mkdir(parents=True, exist_ok=True)

    paths_config_default = PathCofig(
        in_element_path=default_sample_data / piece_default.name,
        out_path=output_path,
        in_name=piece_default.name,
        body_name=config.body_name,
        samples_name='',
        smpl_body=True,
        bodies_default_path=bodies_default_path,
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
    command_args: argparse.Namespace,
    pattern_data: dict[str, PatternData],
    sim_config: SimulationConfig | None = None
) -> bool:
    """Run simulation on an existing dataset.
    
    Parameters
    ----------
    dataset : str
        Name of the dataset folder to simulate.
    command_args : argparse.Namespace
        Parsed command line arguments.
    pattern_data : dict[str, PatternData]
        In-memory pattern data dict mapping pattern names to PatternData objects.
        Required for simulation.
    sim_config : SimulationConfig | None, optional
        Optional simulation configuration object. If provided, will be used instead of
        creating from config file. If None, will create from config file.
    
    Returns
    -------
    bool
        True if simulation finished successfully, False otherwise.
    """
    body_type = 'default_body'
    logger.info("Using default body configuration (default_body)")
    output_path = Path(command_args.datasets_sim) / dataset / body_type
    output_path.mkdir(parents=True, exist_ok=True)
    
    if sim_config is None:
        if command_args.config is not None:
            config_path = Path(command_args.sim_configs_path) / command_args.config
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
        caching=command_args.caching
    )
    
    return finished


def run_pipeline(command_args: argparse.Namespace) -> None:
    """Run the entire pipeline for pattern generation and simulation."""
    output_name = (
        command_args.name 
        if not command_args.batch_id
        else f'{command_args.name}_{command_args.batch_id}'
    )
    config = CLIPatternConfig(
        design_file=Path(command_args.design),
        body_name=command_args.body_name,
        output_name=output_name,
        perfect_fit=command_args.perfect_fit,
        to_subfolders=True
    )
    logger.debug(f"Created pattern config: {config}")
    
    # Get patterns_path from command args
    patterns_path = Path(command_args.output) / command_args.patterns_path
    datasets_sim_path = Path(command_args.output) / command_args.datasets_sim
    
    # Generate pattern
    _, default_pattern_data = generate_sewing_pattern(
        patterns_path,
        config,
        command_args.bodies_default_path,
        str(datasets_sim_path),
        verbose=command_args.verbose
    )
    dataset_name = config.pattern_output_name
    logger.info(f'Pattern generation completed! Output folder: {dataset_name}')
            
    # Step 2: Run simulation if not skipped
    if not command_args.skip_simulation:
        # Create SimulationConfig (for in-memory use)
        if command_args.config is not None:
            config_path = Path(command_args.sim_configs_path) / command_args.config
            logger.info(f"Loading simulation config from: {config_path}")
            sim_config_for_sim = SimulationConfig.from_config_file(config_path, dataset_name)
        else:
            sim_config_for_sim = SimulationConfig.create_default(dataset_name)
        
        run_simulation(dataset_name, command_args, default_pattern_data, sim_config_for_sim)
    else:
        logger.info('Simulation skipped')


if __name__ == "__main__":
    command_args = get_command_args()
    run_pipeline(command_args)