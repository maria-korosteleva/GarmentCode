"""
Grid simulation runner for parameter sweeps.

This script executes the simulation pipeline with different parameter combinations
from a grid configuration file. It handles failures gracefully and continues with
the next parameter set.

Usage:
    python run_grid_simulation.py --grid-config <grid_config.yaml> [options]

The grid config YAML should specify parameter ranges for:
- Design parameters (from enums in perfect_fit_templates/pants_templates.py)
- Material properties (garment_density, garment_radius, garment_tri_ke, etc.)
"""

import argparse
import gc
import itertools
import json
import tempfile
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

from pattern_data_sim import (
    generate_sewing_pattern,
    run_simulation
)
from pygarment.meshgen.cli_pattern_config import CLIPatternConfig
from pygarment.meshgen.pattern_data import SimulationConfig
from config.garment_properties import GarmentMaterialProperties
from config.sim_config import SimConfig
from log_config import set_log_level
from experiment_tracker import ExperimentTracker, MLflowConfig


def parse_grid_config(config_path: Path) -> dict[str, Any]:
    """Parse grid configuration YAML file.
    
    Parameters
    ----------
    config_path : Path
        Path to the grid configuration YAML file.
    
    Returns
    -------
    dict[str, Any]
        Parsed grid configuration dictionary.
    
    Raises
    ------
    FileNotFoundError
        If the config file doesn't exist.
    ValueError
        If the config file is invalid.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Grid config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if not config:
        raise ValueError(f"Grid config file is empty: {config_path}")
    
    return config


def generate_parameter_combinations(grid_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate all parameter combinations from grid configuration.
    
    Parameters
    ----------
    grid_config : dict[str, Any]
        Grid configuration dictionary with parameter lists.
    
    Returns
    -------
    list[dict[str, Any]]
        List of parameter combination dictionaries.
    """
    # Extract parameter lists
    design_params = {}
    material_params = {}
    
    # Design parameters (from enums)
    design_param_keys = [
        'garment_type',
        'raise_to_waist_ratio',
        'crotch_displacement_ratio',
        'leg_length_ratio',
        'general_fit_ratio',
        'pants_style_spec'
    ]
    
    # Material properties
    material_param_keys = [
        'garment_density',
        'garment_radius',
        'garment_tri_ke',
        'garment_tri_kd',
        'garment_tri_ka'
    ]
    
    # Extract design parameters
    for key in design_param_keys:
        if key in grid_config:
            design_params[key] = grid_config[key]
    
    # Extract material parameters
    for key in material_param_keys:
        if key in grid_config:
            material_params[key] = grid_config[key]
    
    # Generate all combinations
    all_combinations = []
    
    # Get all design parameter combinations
    design_keys = list(design_params.keys())
    design_values = [design_params[k] for k in design_keys]
    
    # Get all material parameter combinations
    material_keys = list(material_params.keys())
    material_values = [material_params[k] for k in material_keys]
    
    # Generate Cartesian product of all combinations
    for design_combo in itertools.product(*design_values):
        design_dict = dict(zip(design_keys, design_combo))
        
        for material_combo in itertools.product(*material_values):
            material_dict = dict(zip(material_keys, material_combo))
            
            # Combine into single parameter set
            combo = {**design_dict, **material_dict}
            
            # Add optional name if specified
            if 'name' in grid_config:
                combo['name'] = grid_config['name']
            
            all_combinations.append(combo)
    
    return all_combinations


def generate_name_from_params(params: dict[str, Any]) -> str:
    """Generate a name from parameter values.
    
    Parameters
    ----------
    params : dict[str, Any]
        Parameter dictionary.
    
    Returns
    -------
    str
        Generated name string.
    """
    # Design parameters
    design_parts = []
    design_keys = [
        'raise_to_waist_ratio',
        'crotch_displacement_ratio',
        'leg_length_ratio',
        'general_fit_ratio',
        'pants_style_spec'
    ]
    
    for key in design_keys:
        if key in params:
            design_parts.append(str(params[key]))
    
    # Material parameters (use short names)
    material_parts = []
    if 'garment_density' in params:
        material_parts.append(f"d{params['garment_density']}")
    if 'garment_radius' in params:
        material_parts.append(f"r{params['garment_radius']}")
    if 'garment_tri_ke' in params:
        material_parts.append(f"ke{params['garment_tri_ke']}")
    if 'garment_tri_kd' in params:
        material_parts.append(f"kd{params['garment_tri_kd']}")
    if 'garment_tri_ka' in params:
        material_parts.append(f"ka{params['garment_tri_ka']}")
    
    # Combine parts
    name_parts = design_parts + material_parts
    return "_".join(name_parts).replace(".", "p").replace("-", "_")


def create_design_yaml(params: dict[str, Any], output_path: Path) -> None:
    """Create a perfect fit design YAML file from parameters.
    
    Parameters
    ----------
    params : dict[str, Any]
        Parameter dictionary containing design parameters.
    output_path : Path
        Path where the design YAML file will be written.
    """
    design_dict = {
        'garment_type': params.get('garment_type', 'pants'),
        'raise_to_waist_ratio': params.get('raise_to_waist_ratio', 'MID'),
        'crotch_displacement_ratio': params.get('crotch_displacement_ratio', 'LOW_CROTCH'),
        'leg_length_ratio': params.get('leg_length_ratio', 'ANKLE'),
        'general_fit_ratio': params.get('general_fit_ratio', 'REGULAR'),
        'pants_style_spec': params.get('pants_style_spec', 'STRAIGHT')
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(design_dict, f, default_flow_style=False, sort_keys=False)


def create_simulation_config(
    params: dict[str, Any],
    dataset_name: str,
    base_args: argparse.Namespace
) -> SimulationConfig:
    """Create a SimulationConfig with custom material properties.
    
    This function follows the same logic as pattern_data_sim.py:
    1. Loads default sim props from config file (or uses defaults)
    2. Overwrites material properties with grid parameters
    
    Parameters
    ----------
    params : dict[str, Any]
        Parameter dictionary containing material properties.
    dataset_name : str
        Name of the dataset.
    base_args : argparse.Namespace
        Command line arguments containing config path information.
    
    Returns
    -------
    SimulationConfig
        Simulation configuration with custom material properties.
    """
    # Load default sim props using the same logic as pattern_data_sim.py
    if base_args.config is not None:
        config_path = Path(base_args.sim_configs_path) / base_args.config
        if config_path.exists():
            logger.debug(f"Loading simulation config from: {config_path}")
            base_config = SimulationConfig.from_config_file(config_path, dataset_name)
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            base_config = SimulationConfig.create_default(dataset_name)
    else:
        logger.debug("No config specified, using default simulation config")
        base_config = SimulationConfig.create_default(dataset_name)
    
    # Extract material properties from params
    material_updates = {}
    material_keys = [
        'garment_density',
        'garment_radius',
        'garment_tri_ke',
        'garment_tri_kd',
        'garment_tri_ka'
    ]
    
    for key in material_keys:
        if key in params:
            material_updates[key] = params[key]
    
    # Update material properties if any are specified
    if material_updates:
        # Get current material properties from the loaded config
        current_material = base_config.sim_config.properties.model_dump()
        
        # Handle backward compatibility: map fabric_density/fabric_thickness if present
        # (from old YAML configs) to garment_density/garment_radius
        material_dict = base_config.sim_config._props.get('material', {})
        if 'fabric_density' in material_dict and 'garment_density' not in current_material:
            current_material['garment_density'] = material_dict['fabric_density']
        if 'fabric_thickness' in material_dict and 'garment_radius' not in current_material:
            current_material['garment_radius'] = material_dict['fabric_thickness']
        
        # Apply grid parameter updates (these override the defaults)
        logger.debug(f"Updating material properties: {material_updates}")
        current_material.update(material_updates)
        
        # Create new material properties object
        updated_material = GarmentMaterialProperties(**current_material)
        
        # Create new sim config dict with updated material
        sim_config_dict = base_config.sim_config._props.copy()
        sim_config_dict['material'] = updated_material.model_dump()
        
        # Create new SimConfig
        new_sim_config = SimConfig(sim_config_dict)
        
        # Create new SimulationConfig
        return SimulationConfig(
            sim_config=new_sim_config,
            render_config=base_config.render_config,
            data_folder=dataset_name
        )
    
    return base_config


def clear_gpu_memory():
    """Clear GPU memory cache to prevent accumulation between simulations."""
    # Clear Python garbage collection
    gc.collect()
    logger.debug("Cleared Warp GPU memory via garbage collection")


def load_mlflow_config(config_path: Optional[Path] = None) -> Optional[MLflowConfig]:
    """Load MLflow configuration from JSON file.
    
    Parameters
    ----------
    config_path : Path, optional
        Path to MLflow config JSON file. If None, tries default location.
    
    Returns
    -------
    MLflowConfig or None
        MLflow configuration object, or None if config not found or disabled.
    """
    if config_path is None:
        config_path = Path("config/mlflow_config.json")
    
    if not config_path.exists():
        logger.debug(f"MLflow config not found at {config_path}, tracking disabled")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        if not config_dict.get('enabled', True):
            logger.debug("MLflow tracking is disabled in config")
            return None
        
        return MLflowConfig(**config_dict)
    except Exception as e:
        logger.warning(f"Failed to load MLflow config: {e}, tracking disabled")
        return None


def run_single_simulation(
    params: dict[str, Any],
    base_args: argparse.Namespace,
    experiment_tracker: Optional[ExperimentTracker] = None
) -> tuple[bool, str]:
    """Run a single simulation with given parameters.
    
    Parameters
    ----------
    params : dict[str, Any]
        Parameter dictionary for this simulation.
    base_args : argparse.Namespace
        Base command line arguments from pattern_data_sim.py.
    
    Returns
    -------
    tuple[bool, str]
        Tuple of (success: bool, message: str).
    """
    # Clear GPU memory before starting new simulation
    clear_gpu_memory()
    
    # Generate name for this simulation
    if 'name' in params and params['name']:
        dataset_name = params['name']
    else:
        dataset_name = generate_name_from_params(params)
    
    logger.info(f"Running simulation: {dataset_name}")
    logger.debug(f"Parameters: {params}")
    
    try:
        # Create temporary design YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
            tmp_design_path = Path(tmp_file.name)
            create_design_yaml(params, tmp_design_path)
        
        try:
            # Create pattern config
            config = CLIPatternConfig(
                design_file=tmp_design_path,
                body_name=base_args.body_name,
                output_name=dataset_name,
                perfect_fit=True,  # Always use perfect fit mode
                to_subfolders=True
            )
            
            # Get paths
            patterns_path = Path(base_args.output) / base_args.patterns_path
            datasets_sim_path = Path(base_args.output) / base_args.datasets_sim
            
            # Generate pattern
            logger.info(f"Generating pattern for {dataset_name}...")
            default_pattern_data = generate_sewing_pattern(
                patterns_path,
                config,
                base_args.bodies_default_path,
                str(datasets_sim_path),
                verbose=base_args.verbose
            )
            
            dataset_name_actual = config.pattern_output_name
            logger.info(f"Pattern generation completed: {dataset_name_actual}")
            
            # Initialize experiment tracker for this simulation if not provided
            tracker = experiment_tracker
            if tracker is None:
                mlflow_config = load_mlflow_config()
                if mlflow_config is not None:
                    # Use base name with parameter variations (without date suffix) for experiment name
                    tracker = ExperimentTracker(mlflow_config, exp_name=dataset_name)
            
            # Log parameters to tracker if available
            if tracker is not None:
                try:
                    # Log design parameters
                    design_params = {
                        f"design_{k}": v
                        for k, v in params.items()
                        if k in [
                            'garment_type',
                            'raise_to_waist_ratio',
                            'crotch_displacement_ratio',
                            'leg_length_ratio',
                            'general_fit_ratio',
                            'pants_style_spec'
                        ]
                    }
                    # Log material parameters
                    material_params = {
                        f"material_{k}": v
                        for k, v in params.items()
                        if k in [
                            'garment_density',
                            'garment_radius',
                            'garment_tri_ke',
                            'garment_tri_kd',
                            'garment_tri_ka'
                        ]
                    }
                    tracker.log_params({**design_params, **material_params})
                except Exception as e:
                    logger.warning(f"Failed to log parameters to tracker: {e}")
            
            # Create simulation config with custom material properties
            # This loads default sim props and then overwrites with grid params
            sim_config = create_simulation_config(
                params,
                dataset_name_actual,
                base_args
            )
            
            # Run simulation
            if not base_args.skip_simulation:
                logger.info(f"Running simulation for {dataset_name_actual}...")
                success = False
                try:
                    success = run_simulation(
                        dataset_name_actual,
                        base_args,
                        default_pattern_data,
                        sim_config=sim_config,
                        experiment_tracker=tracker
                    )
                finally:
                    # Always clear GPU memory after simulation, even if it failed
                    clear_gpu_memory()
                    # End tracker run if we created it locally
                    if tracker is not None and experiment_tracker is None:
                        tracker.end_run()
                        # Reset singleton instance for next simulation
                        # This allows each simulation in the grid to have its own experiment
                        ExperimentTracker._instance = None
                        ExperimentTracker._initialized = False
                if success:
                    logger.info(f"Simulation completed successfully: {dataset_name_actual}")
                    return True, f"Success: {dataset_name_actual}"
                else:
                    logger.warning(f"Simulation failed: {dataset_name_actual}")
                    return False, f"Simulation failed: {dataset_name_actual}"
            else:
                logger.info(f"Simulation skipped for {dataset_name_actual}")
                return True, f"Pattern generated (simulation skipped): {dataset_name_actual}"
        
        finally:
            # Clean up temporary design file
            if tmp_design_path.exists():
                tmp_design_path.unlink()
    
    except Exception as e:
        error_msg = f"Error in simulation {dataset_name}: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        # Clear GPU memory even on error
        clear_gpu_memory()
        return False, error_msg


def get_command_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns
    -------
    argparse.Namespace
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='Run grid simulation with parameter sweeps'
    )
    
    parser.add_argument(
        '--grid-config', '-g',
        help='Path to grid configuration YAML file',
        type=str,
        required=True
    )
    
    parser.add_argument(
        '--base-config', '-c',
        help='Path to base simulation config file (optional)',
        type=str,
        default=None
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose output'
    )
    
    parser.add_argument(
        '--skip-simulation',
        action='store_true',
        help='Skip simulation, only generate patterns'
    )
    
    parser.add_argument(
        '--caching',
        action='store_true',
        help='Cache intermediate simulation results'
    )
    
    # Pass through arguments for pattern_data_sim.py
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
    
    parser.add_argument(
        "--mlflow-config",
        help='Path to MLflow configuration JSON file',
        type=str,
        default=None
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        set_log_level("DEBUG")
        logger.debug(f'Command line arguments: {args}')
    else:
        set_log_level("INFO")
    
    return args


def main():
    """Main entry point for grid simulation."""
    args = get_command_args()
    
    # Parse grid configuration
    grid_config_path = Path(args.grid_config)
    logger.info(f"Loading grid configuration from: {grid_config_path}")
    grid_config = parse_grid_config(grid_config_path)
    
    # Generate all parameter combinations
    logger.info("Generating parameter combinations...")
    combinations = generate_parameter_combinations(grid_config)
    logger.info(f"Generated {len(combinations)} parameter combinations")
    
    # Determine config file to use (same logic as pattern_data_sim.py)
    # If base_config is provided, use it; otherwise use default
    config_file = args.base_config if args.base_config else "default_sim_props.yaml"
    
    # Create base args namespace for pattern_data_sim functions
    # Use argparse.Namespace to create a compatible namespace
    base_args = argparse.Namespace(
        body_name=args.body_name,
        bodies_default_path=args.bodies_default_path,
        body_samples_path=args.body_samples_path,
        output=args.output,
        patterns_path=args.patterns_path,
        datasets_sim=args.datasets_sim,
        sim_configs_path=args.sim_configs_path,
        config=config_file,  # Use the determined config file
        verbose=args.verbose,
        skip_simulation=args.skip_simulation,
        caching=args.caching
    )
    
    # Run simulations for each combination
    results = []
    successful = 0
    failed = 0
    
    for i, params in enumerate(combinations, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Running simulation {i}/{len(combinations)}")
        logger.info(f"{'='*80}")
        
        success, message = run_single_simulation(params, base_args)
        results.append((params, success, message))
        
        if success:
            successful += 1
        else:
            failed += 1
    
    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info("GRID SIMULATION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total simulations: {len(combinations)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info("\nFailed simulations:")
    
    for params, success, message in results:
        if not success:
            logger.info(f"  - {message}")
            if args.verbose:
                logger.debug(f"    Parameters: {params}")


if __name__ == "__main__":
    main()

