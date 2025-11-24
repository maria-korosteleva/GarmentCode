"""Routines to run cloth simulation"""

# Basic
import time
import multiprocessing
import platform
import signal
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# BoxMeshGen
import pygarment.meshgen.boxmeshgen as bmg
from pygarment.meshgen.boxmeshgen import BoxMesh
from config import PathCofig
from config.dataset_properties import DatasetProperties

# Warp simulation
from pygarment.meshgen.simulation import run_sim
from pygarment.meshgen.garment_data import GarmentData

# For loading body mesh
import igl
import json


def batch_sim_with_data(
    pattern_data: dict[str, dict[str, Any]],
    data_path: Path,
    output_path: Path,
    dataset_props: Any,
    run_default_body: bool = False,
    num_samples: Optional[int] = None,
    caching: bool = False,
    force_restart: bool = False
) -> bool:
    """Perform pattern simulation using in-memory pattern data.
    
    Similar to `batch_sim` but uses pattern data passed directly instead of reading
    from disk. Data is still saved to disk for backup, but simulation uses the
    in-memory structures for improved performance.
    
    Parameters
    ----------
    pattern_data : dict[str, dict[str, Any]]
        Dictionary mapping pattern names to their data structures.
        Format: {pattern_name: {'piece': ..., 'body_params': ..., 'body_def': ..., 'design': ...}}
    data_path : Path
        Path to folder with patterns (for given body type). Used for output paths
        and file structure.
    output_path : Path
        Path to folder where the simulated dataset will be saved.
    dataset_props : Any
        Dataset properties object (same as `batch_sim`). Must support dictionary-like
        access with keys 'sim', 'body_default', 'body_samples', and 'frozen'.
    run_default_body : bool, optional
        If True, runs the dataset on the default body. Default is False.
    num_samples : int, optional
        Number of samples to process in this batch. If None, processes all samples.
        Default is None.
    caching : bool, optional
        If True, enables caching of every frame of simulation. This significantly
        slows down simulation. Default is False.
    force_restart : bool, optional
        If True, forces restarting the batch processing even if resume conditions
        are met. Default is False.

    Returns
    -------
    bool
        True if all samples were processed successfully, False otherwise.
        
    Note
    ----
    This function automatically handles resuming from the last processed pattern
    unless `force_restart` is True. Progress is saved periodically to allow safe
    interruption and resumption.
    """
    # ----- Init -----
    if 'frozen' in dataset_props and dataset_props['frozen']:
        logger.warning('Dataset is frozen, processing is skipped')
        return True

    resume = init_sim_props(dataset_props, batch_run=True, force_restart=force_restart)
    body_type = 'default_body' if run_default_body else 'random_body'
    data_props_file = output_path / f'dataset_properties_{body_type}.yaml'
    
    # Convert to DatasetProperties for type-safe config access
    # Note: stats are still accessed via dict since they're runtime data
    dataset_props_obj = DatasetProperties.from_props(dataset_props)
    
    # Get pattern names from in-memory data
    pattern_names = list(pattern_data.keys())
    total_patterns = len(pattern_names)
    logger.info(f"Starting batch simulation with in-memory data: {total_patterns} patterns found (body_type: {body_type})")
    if num_samples is not None:
        logger.info(f"Processing {num_samples} samples in this batch")

    # Simulate every template
    count = 0
    for pattern_name in pattern_names:
        # Skip processed cases -- in case of resume
        # Stats are runtime data, so we access via dict
        if resume and pattern_name in dataset_props_obj.sim.stats.get('processed', []):
            logger.debug(f'Skipped as already processed: {pattern_name}')
            continue

        # Initialize processed list if needed
        if 'processed' not in dataset_props_obj.sim.stats:
            dataset_props_obj.sim.stats['processed'] = []
        dataset_props_obj.sim.stats['processed'].append(pattern_name)
        # Update props before serialization
        dataset_props_obj.update_props(dataset_props)
        _serialize_props_with_sim_stats(dataset_props, data_props_file)  # Save before potential crash

        try:
            # Create paths config (still needed for output structure)
            paths = PathCofig(
                in_element_path=data_path / pattern_name,
                out_path=output_path,
                in_name=pattern_name,
                body_name=dataset_props['body_default'],
                samples_name=dataset_props['body_samples'],
                default_body=run_default_body
            )
            
            # Use in-memory pattern data
            pattern_info = pattern_data[pattern_name]
            attachment_constraints = pattern_info.get('attachment_constraints', None)
            template_simulation_with_data(
                paths, 
                dataset_props, 
                pattern_info['piece'],
                pattern_info['body_params'],
                pattern_info['body_def'],
                pattern_info['design'],
                caching=caching,
                attachment_constraints=attachment_constraints
            )
        except BaseException as e: 
            # Not all files available
            logger.error(f"Pattern simulation failed for {pattern_name}: {e}")
            dataset_props.add_fail('sim', 'crashes', pattern_name)

        count += 1  # count actively processed cases
        
        # Log progress periodically
        if count % 10 == 0:
            logger.info(f'Processed {count} patterns...')
        
        if num_samples is not None and count >= num_samples:  # Process requested number of samples
            logger.info(f"Batch limit reached ({num_samples} samples processed)")
            break

    # Check completion status
    # Refresh dataset_props_obj to get latest stats
    dataset_props_obj = DatasetProperties.from_props(dataset_props)
    processed_count = len(dataset_props_obj.sim.stats.get('processed', []))
    logger.info(f'\nFinished batch processing: {processed_count}/{total_patterns} patterns processed')
    
    try:
        if processed_count >= total_patterns:
            # Processing successfully finished -- no need to resume later
            if 'processed' in dataset_props_obj.sim.stats:
                del dataset_props_obj.sim.stats['processed']
            dataset_props['frozen'] = True
            dataset_props_obj.update_props(dataset_props)
            process_finished = True
            logger.success("All patterns processed successfully. Dataset frozen.")
        else:
            process_finished = False
            logger.warning(f"Processing incomplete: {processed_count}/{total_patterns} patterns processed")
    except KeyError:
        logger.warning('KeyError accessing processed stats')
        process_finished = True

    # Logs - update props before serialization
    dataset_props_obj.update_props(dataset_props)
    _serialize_props_with_sim_stats(dataset_props, data_props_file)

    return process_finished


def batch_sim(data_path, output_path, dataset_props,
              run_default_body=False, num_samples=None, caching=False, force_restart=False):
    """
    Performs pattern simulation for each example in the dataset given by dataset_props.
    Batch processing is automatically resumed from the last unprocessed datapoint if restart is not forced.
    
    Parameters:
    -----------
    data_path : Path
        Path to folder with patterns (for given body type)
    output_path : Path
        Path to folder with the simulated dataset
    dataset_props : Properties
        Dataset properties. Must contain:
        - Dataset folder (inside data_path)
        - Type of dataset structure (with/without subfolders for patterns)
        - List of processed samples if processing of dataset was already attempted
        - Simulation parameters
        - Rendering parameters
        Other needed properties will be files with default values if the corresponding sections
        are not found in props object
    run_default_body : bool, optional
        Runs the dataset on the default body (disabled by default)
    num_samples : int, optional
        Number of (unprocessed) samples from dataset to process with this run.
        If None, runs over all unprocessed samples (useful for batching in the future)
    caching : bool, optional
        Enables caching of every frame of simulation (disabled by default)
    force_restart : bool, optional
        Force restarting the batch processing even if resume conditions are met.

    Returns:
    --------
    bool
        True if all samples were processed successfully, False otherwise
    """
    # ----- Init -----
    if 'frozen' in dataset_props and dataset_props['frozen']:
        logger.warning('Dataset is frozen, processing is skipped')
        return True

    resume = init_sim_props(dataset_props, batch_run=True, force_restart=force_restart)
    body_type = 'default_body' if run_default_body else 'random_body'
    data_props_file = output_path / f'dataset_properties_{body_type}.yaml'
    
    # Convert to DatasetProperties for type-safe config access
    # Note: stats are still accessed via dict since they're runtime data
    dataset_props_obj = DatasetProperties.from_props(dataset_props)
    
    pattern_names = _get_pattern_names(data_path)

    total_patterns = len(pattern_names)
    logger.info(f"Starting batch simulation: {total_patterns} patterns found (body_type: {body_type})")
    if num_samples is not None:
        logger.info(f"Processing {num_samples} samples in this batch")

    # Simulate every template
    count = 0
    for pattern_name in pattern_names:
        # Skip processed cases -- in case of resume
        # Stats are runtime data, so we access via dict
        if resume and pattern_name in dataset_props_obj.sim.stats.get('processed', []):
            logger.debug(f'Skipped as already processed: {pattern_name}')
            continue

        # Initialize processed list if needed
        if 'processed' not in dataset_props_obj.sim.stats:
            dataset_props_obj.sim.stats['processed'] = []
        dataset_props_obj.sim.stats['processed'].append(pattern_name)
        # Update props before serialization
        dataset_props_obj.update_props(dataset_props)
        _serialize_props_with_sim_stats(dataset_props, data_props_file)  # Save before potential crash

        try:
            paths = PathCofig(
                in_element_path=data_path / pattern_name,
                out_path=output_path,
                in_name=pattern_name,
                body_name=dataset_props['body_default'],
                samples_name=dataset_props['body_samples'],
                default_body=run_default_body
            )
        except BaseException as e: 
            # Not all files available
            logger.error(f"Pattern loading failed (paths) for {pattern_name}: {e}")
            dataset_props.add_fail('sim', 'crashes', pattern_name)
        else:
            template_simulation(paths, dataset_props, caching=caching)

        count += 1  # count actively processed cases
        
        # Log progress periodically
        if count % 10 == 0:
            logger.info(f'Processed {count} patterns...')
        
        if num_samples is not None and count >= num_samples:  # Process requested number of samples
            logger.info(f"Batch limit reached ({num_samples} samples processed)")
            break

    # Check completion status
    # Refresh dataset_props_obj to get latest stats
    dataset_props_obj = DatasetProperties.from_props(dataset_props)
    processed_count = len(dataset_props_obj.sim.stats.get('processed', []))
    logger.info(f'\nFinished batch processing: {processed_count}/{total_patterns} patterns processed')
    
    try:
        if processed_count >= total_patterns:
            # Processing successfully finished -- no need to resume later
            if 'processed' in dataset_props_obj.sim.stats:
                del dataset_props_obj.sim.stats['processed']
            dataset_props['frozen'] = True
            dataset_props_obj.update_props(dataset_props)
            process_finished = True
            logger.success("All patterns processed successfully. Dataset frozen.")
        else:
            process_finished = False
            logger.warning(f"Processing incomplete: {processed_count}/{total_patterns} patterns processed")
    except KeyError:
        logger.warning('KeyError accessing processed stats')
        process_finished = True

    # Logs - update props before serialization
    dataset_props_obj.update_props(dataset_props)
    _serialize_props_with_sim_stats(dataset_props, data_props_file)

    return process_finished


# ------- Utils -------
def init_sim_props(props, batch_run=False, force_restart=False):
    """
    Add default config values if not given in props & clean-up stats if not resuming previous processing
    Returns a flag whether current simulation is a resumed last one
    
    Parameters:
    -----------
    props : Properties
        Properties object to initialize
    batch_run : bool, optional
        Whether this is a batch run
    force_restart : bool, optional
        Force restart even if resume is possible

    Returns:
    --------
    bool
        True if resuming, False if starting fresh
    """
    if 'sim' not in props:
        props.set_section_config(
            'sim',
            config={
                'control': {
                    'max_sim_steps': 1000,
                    'max_frame_time': 15,  # in seconds
                    'max_sim_time': 1500,  # in seconds
                    'zero_gravity_steps': 10,
                    'static_threshold': 0.03,
                    'non_static_percent': 1.5,
                    'max_body_collisions': 0,
                    'max_self_collisions': 0,
                    'resolution_scale': 1.0,
                    'ground': False,  # Do not add floor s.t. garment falls infinitely if falls
                },
                'material': {},
                'options': {},
                'max_meshgen_time': 20,  # Legacy parameter, in seconds
            }
        )

    config_dict = props['sim']['config']
    
    # Ensure control section exists
    if 'control' not in config_dict:
        config_dict['control'] = {}
    
    # Ensure material section exists
    if 'material' not in config_dict or not config_dict['material']:
        config_dict['material'] = {  
            'garment_tri_ka': 10000.0,  
            'garment_edge_ke': 1.0,  
            'garment_tri_ke': 10000.0,
            'spring_ke': 50000.0,  
            'garment_edge_kd': 10.0,
            'garment_tri_kd': 1.0,  
            'spring_kd': 10.0, 
            'fabric_density':  1.0,  
            'fabric_thickness': 0.1,
            'fabric_friction': 0.5
        }

    # Ensure options section exists
    if 'options' not in config_dict or not config_dict['options']:
        config_dict['options'] = {
            'enable_particle_particle_collisions': False,
            'enable_triangle_particle_collisions': True, 
            'enable_edge_edge_collisions': True,
            'enable_body_collision_filters': True,
            'enable_attachment_constraint': True,   
            'attachment_frames': 400, 
            'attachment_label_names': ['lower_interface'],
            'attachment_stiffness': [1000.],
            'attachment_damping': [10.], 
            'global_damping_factor': 0.25,
            'global_damping_effective_velocity': 0.0,
            'global_max_velocity': 25.0,
            'enable_global_collision_filter': True,
            'enable_cloth_reference_drag': False,    
            'cloth_reference_margin': 0.1,
            'enable_body_smoothing': False,  
            'smoothing_total_smoothing_factor': 1.0,
            'smoothing_recover_start_frame': 150,
            'smoothing_num_steps': 100,
            'smoothing_frame_gap_between_steps': 1,
            'body_collision_thickness': 0.25,
            'body_friction': 0.5
        }

    if 'render' not in props:
        # init with defaults
        props.set_section_config(
            'render',
            resolution=[800, 800],
            sides=['front','back'],
            front_camera_location=None,
            uv_texture={
                'seam_width': 0.5,
                'dpi': 1500,
                'fabric_grain_texture_path': None,
                'fabric_grain_resolution': 5,
            }
        )

    if batch_run and 'processed' in props['sim']['stats'] and not force_restart:
        # Resuming existing batch processing -- do not clean stats
        # Check if processed list is not empty before accessing
        processed_list = props['sim']['stats']['processed']
        if not processed_list:
            # No processed items, start fresh
            logger.info("No processed items found, starting fresh batch processing")
        else:
            # Assuming the last example processed example caused the failure
            last_processed = processed_list[-1]

            # Access render stats through DatasetProperties for type safety
            dataset_props_temp = DatasetProperties.from_props(props)
            render_time_keys = dataset_props_temp.render.stats.get('render_time', {}).keys()
            if not any([(name in last_processed) or (last_processed in name) for name in render_time_keys]):
                # Crash detected -- the last example does not appear in the stats
                # Stats are runtime data, so we access via dict
                if last_processed not in dataset_props_temp.sim.stats.get('fails', {}).get('crashes', []):
                    # Remove last from processed if it did not crash
                    if last_processed not in dataset_props_temp.sim.stats.get('stop_over', []):   
                        dataset_props_temp.sim.stats.setdefault('processed', []).pop()
                        dataset_props_temp.update_props(props)
                        logger.debug(f"Removed last processed pattern (likely crashed): {last_processed}")
                    else:
                        # Already passed here once -> add as crash
                        dataset_props_temp.sim.stats.setdefault('fails', {}).setdefault('crashes', []).append(last_processed)
                        dataset_props_temp.update_props(props)
                        logger.warning(f"Marking pattern as crash (second attempt): {last_processed}")

            # Indicate resuming dataset simulation
            dataset_props_temp.sim.stats.setdefault('stop_over', []).append(last_processed)
            dataset_props_temp.update_props(props)
            logger.info(f"Resuming batch processing from: {last_processed}")
            return True

    # Starting fresh - prepare cumulative stats
    props.set_section_stats('sim', 
                            fails={}, 
                            meshgen_time={}, 
                            sim_time={}, 
                            spf={}, 
                            fin_frame={}, 
                            face_count={},
                            body_collisions={}, 
                            self_collisions={})
    props['sim']['stats']['fails'] = {
        'crashes': [],
        'cloth_body_intersection': [],
        'cloth_self_intersection': [],
        'static_equilibrium': [],
        'fast_finish': [],
        'pattern_loading': [],
        'multi_stitching': [],
        'gt_edges_creation': []
    }

    props.set_section_stats('render', render_time={})

    if batch_run:  # track batch processing
        props.set_section_stats('sim', processed=[], stop_over=[])

    logger.debug("Initialized simulation properties for new batch run")
    return False


def template_simulation_with_data(
    paths: PathCofig,
    props: Any,  # Properties object with dict-like access and add_fail method
    piece: Any,
    body_params: Any,
    body_def: Any,
    design: dict[str, Any],
    caching: bool = False,
    attachment_constraints: list[Any] | None = None
) -> None:
    """Simulate a garment template using in-memory pattern data.
    
    This function uses pattern data passed directly instead of reading from disk.
    The data is still saved to disk for backup and compatibility, but simulation
    uses the in-memory structures for improved performance.
    
    Parameters
    ----------
    paths : PathCofig
        Path configuration object containing all necessary file paths.
    props : dict[str, Any]
        Dictionary containing simulation and render properties. Must have keys:
        - 'sim': Dictionary with simulation configuration
        - 'render': Dictionary with rendering configuration
    piece : Any
        Garment piece object. Must have an `assembly()` method that returns a
        pattern object with a `serialize()` method.
    body_params : Any
        Body parameters object. Must have a `save()` method that accepts a path.
    body_def : Any
        Body definition object for accessing body measurements and parameters.
    design : dict[str, Any]
        Design parameters dictionary to be saved to disk.
    caching : bool, optional
        If True, enables caching of every frame of simulation. This significantly
        slows down simulation. Default is False.
    attachment_constraints : list[AttachmentConstraint] | None, optional
        Optional list of attachment constraints to inject into the simulation config.
        If provided, these constraints will be added to the config before simulation.
        Default is None.
        
    Note
    ----
    This function ensures that all necessary files are saved to disk (if they
    don't already exist) before running the simulation. This maintains backward
    compatibility and allows for later disk-based processing or debugging.
    
    If attachment_constraints are provided, they will be injected into the
    simulation config (props['sim']['config']['options']['attachment_constraints'])
    before creating the SimConfig object. This allows garment-specific constraints
    to be used during simulation.
    
    Raises
    ------
    TimeoutError
        If mesh generation takes longer than the configured timeout.
    PatternLoadingError
        If the pattern cannot be loaded correctly.
    BaseException
        If any other error occurs during pattern loading or simulation.
    """
    # Convert props to DatasetProperties for class-based access
    dataset_props = DatasetProperties.from_props(props)
    
    # Inject attachment constraints into config if provided (using classes)
    if attachment_constraints is not None and len(attachment_constraints) > 0:
        dataset_props.update_attachment_constraints(attachment_constraints)
        # Write back to props dict for serialization
        dataset_props.update_props(props)
        logger.debug(f'Injected {len(attachment_constraints)} attachment constraints into simulation config')
    
    # Ensure pattern data is saved to expected location (for backup)
    pattern = piece.assembly()
    spec_path = paths.in_g_spec
    
    # Only save if file doesn't exist (data should already be saved)
    if not spec_path.exists():
        logger.debug(f'Pattern spec not found at {spec_path}, saving from in-memory data...')
        pattern.serialize(
            spec_path.parent,
            tag='',
            to_subfolder=False,
            with_3d=False,
            with_text=False,
            view_ids=False
        )
    
    # Ensure body measurements are saved
    body_mes_path = paths.input / 'body_measurements.yaml'
    if not body_mes_path.exists():
        body_params.save(paths.input)
    
    # Ensure design params are saved
    design_params_path = paths.in_design_params
    if not design_params_path.exists():
        import yaml
        with open(design_params_path, 'w') as f:
            yaml.dump({'design': design}, f, default_flow_style=False, sort_keys=False)
    
    # Create BoxMesh from pattern and load it
    # Use DatasetProperties class for type-safe config access
    # (dataset_props was already created above if constraints were injected)
    if attachment_constraints is None or len(attachment_constraints) == 0:
        dataset_props = DatasetProperties.from_props(props)
    config = dataset_props.sim.get_sim_config()
    res = config.resolution_scale
    
    garment_box_mesh = BoxMesh(spec_path, res)
    
    # Load BoxMesh with timeout handling (same as template_simulation)
    meshgen_start_time = time.time()
    # max_meshgen_time is an optional config value not in SimConfig classes
    timeout_after = int(dataset_props.sim.get_optional_config_value('max_meshgen_time', 20))
    
    try:
        _load_boxmesh_timeout(garment_box_mesh, timeout_after)
    except TimeoutError as e:
        logger.error(f"Mesh generation timeout for {garment_box_mesh.name}: {e}")
        props.add_fail('sim', 'meshgen-timeout', garment_box_mesh.name)
        return
    except bmg.PatternLoadingError as e:
        logger.error(f"Pattern loading error for {garment_box_mesh.name}: {e}")
        props.add_fail('sim', 'pattern_loading', garment_box_mesh.name)
        return
    except BaseException as e:
        logger.error(f"Pattern loading failed due to unknown error for {garment_box_mesh.name}: {e}")
        logger.exception("Exception details:")
        props.add_fail('sim', 'crashes', garment_box_mesh.name)
        return
    
    # Successfully loaded garment
    dataset_props.sim.stats['meshgen_time'][garment_box_mesh.name] = time.time() - meshgen_start_time
    dataset_props.sim.stats['face_count'][garment_box_mesh.name] = len(garment_box_mesh.faces)
    
    # Serialize BoxMesh (for backup and rendering)
    # Note: store_vertex_normals and store_panels are optional fields in options dict
    options_dict = dataset_props.sim.get_options_dict()
    vertex_normals = options_dict.get('store_vertex_normals', False)
    store_panels = options_dict.get('store_panels', False)
    garment_box_mesh.serialize(
        paths, 
        with_v_norms=vertex_normals, 
        store_panels=store_panels,
        uv_config=dataset_props.render.config.uv_texture.model_dump()
    )
    
    # Load body mesh data (same as load_obj in garment.py)
    body_vertices, body_faces = igl.read_triangle_mesh(str(paths.in_body_obj))
    body_indices = body_faces.flatten()
    
    # Load body segmentation
    with open(paths.body_seg, 'r') as f:
        body_segmentation = json.load(f)
    
    # Extract vertex labels from BoxMesh (if available)
    vertex_labels = garment_box_mesh.vertex_labels if hasattr(garment_box_mesh, 'vertex_labels') and garment_box_mesh.vertex_labels else None
    
    # Create GarmentData object
    garment_data = GarmentData(
        box_mesh=garment_box_mesh,
        body_definition=body_def,
        body_vertices=body_vertices,
        body_indices=body_indices,
        body_faces=body_faces,
        body_segmentation=body_segmentation,
        vertex_labels=vertex_labels
    )
    
    # Run simulation with in-memory data
    logger.debug(f'Running simulation for {garment_box_mesh.name} with in-memory data...')
    run_sim(
        garment_box_mesh.name,  
        props, 
        paths,
        save_v_norms=vertex_normals,  # Already extracted above
        store_usd=caching,
        optimize_storage=dataset_props.sim.get_optional_config_value('optimize_storage', False),
        verbose=False,
        garment_data=garment_data
    )


def template_simulation(paths: PathCofig, props, caching=False):
    """
    Simulate given template within given scene & save log files
    
    Parameters:
    -----------
    paths : PathCofig
        Path configuration object
    props : Properties
        Simulation properties
    caching : bool, optional
        Enable caching of simulation frames
    """
    # Use DatasetProperties class instead of dictionary access
    dataset_props = DatasetProperties.from_props(props)
    config = dataset_props.sim.get_sim_config()
    res = config.resolution_scale

    garment = BoxMesh(paths.in_g_spec, res)

    logger.debug(f'Loading garment: {garment.name}')

    meshgen_start_time = time.time()
    # max_meshgen_time is an optional config value not in SimConfig classes
    timeout_after = int(dataset_props.sim.get_optional_config_value('max_meshgen_time', 20))

    try:
        _load_boxmesh_timeout(garment, timeout_after)
    except TimeoutError as e:
        logger.error(f"Mesh generation timeout for {garment.name}: {e}")
        failure_case = 'meshgen-timeout'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.PatternLoadingError as e:
        logger.error(f"Pattern loading error for {garment.name}: {e}")
        failure_case = 'pattern_loading'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.DegenerateTrianglesError as e:
        logger.error(f"Degenerate triangles error for {garment.name}: {e}")
        failure_case = 'degenerate_triangles'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.MultiStitchingError as e:
        logger.error(f"Multi-stitching error for {garment.name}: {e}")
        failure_case = 'multi_stitching'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.NormError as e:
        logger.error(f"Normal error for {garment.name}: {e}")
        failure_case = 'norm_error'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.StitchingError as e:
        logger.error(f"Stitching error for {garment.name}: {e}")
        failure_case = 'stitching_error'
        props.add_fail('sim', failure_case, garment.name)
    except BaseException as e:
        logger.error(f"Pattern loading failed due to unknown error for {garment.name}: {e}")
        logger.exception("Exception details:")
        failure_case = 'crashes'
        props.add_fail('sim', failure_case, garment.name)
    else:
        # Successfully loaded garment
        dataset_props.sim.stats['meshgen_time'][garment.name] = time.time() - meshgen_start_time
        dataset_props.sim.stats['face_count'][garment.name] = len(garment.faces)
        # Note: store_vertex_normals and store_panels are optional fields in options dict
        options_dict = dataset_props.sim.get_options_dict()
        vertex_normals = options_dict.get('store_vertex_normals', False)
        store_panels = options_dict.get('store_panels', False)
        garment.serialize(
            paths, 
            with_v_norms=vertex_normals, 
            store_panels=store_panels,
            uv_config=dataset_props.render.config.uv_texture.model_dump()
        )

        logger.debug(f'Running simulation for {garment.name}...')
        run_sim(
            garment.name,  
            props, 
            paths,
            save_v_norms=vertex_normals,
            store_usd=caching,  # NOTE: False for fast simulation!
            optimize_storage=dataset_props.sim.get_optional_config_value('optimize_storage', False),
            verbose=False
        )
        logger.debug(f'Simulation completed for {garment.name}')


def _load_boxmesh_timeout(garment, timeout_after):
    """Load boxmesh with timeout protection
    
    Parameters:
    -----------
    garment : BoxMesh
        Garment mesh to load
    timeout_after : int
        Timeout in seconds
    """
    if platform.system() == "Windows":
        # Windows timeout using multiprocessing
        p = multiprocessing.Process(target=garment.load(), name="GarmentGeneration")
        p.start()

        # Wait timeout_after seconds for garment.load()
        time.sleep(timeout_after)

        # If thread is active
        if p.is_alive():
            # Terminate the process
            p.terminate()
            p.join()
            raise TimeoutError(f"Garment loading exceeded timeout of {timeout_after}s")

    elif platform.system() in ["Linux", "OSX"]:
        # Unix timeout using signal
        def alarm_handler(signum, frame):
            raise TimeoutError(f"Garment loading exceeded timeout of {timeout_after}s")

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout_after)
        try:
            garment.load()
        except TimeoutError:
            raise
        finally:
            signal.alarm(0)


def get_dict_default_value(props, name, default_value):
    """Get value from dict with default fallback
    
    Parameters:
    -----------
    props : dict
        Dictionary to query
    name : str
        Key name
    default_value : Any
        Default value if key not found
    
    Returns:
    --------
    Any
        Value from dict or default
    """
    if name in props:
        return props[name]
    return default_value


def _serialize_props_with_sim_stats(dataset_props, filename):
    """Compute data processing statistics and serialize props to file
    
    Parameters:
    -----------
    dataset_props : Properties
        Properties object to serialize
    filename : Path
        Output file path
    """
    dataset_props.stats_summary()
    dataset_props.serialize(filename)


def _get_pattern_names(data_path: Path):
    """Get list of pattern names from data directory
    
    Parameters:
    -----------
    data_path : Path
        Path to data directory
    
    Returns:
    --------
    list[str]
        List of pattern names (directory stems)
    """
    names = []
    to_ignore = ['renders']  # Special dirs not to include in the pattern list
    for el in data_path.iterdir():
        if el.is_dir() and el.stem not in to_ignore:
            names.append(el.stem)

    return names
