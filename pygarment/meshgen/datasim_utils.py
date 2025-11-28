"""Routines to run cloth simulation"""

import time
import multiprocessing
import platform
import signal
from typing import Any, Optional

from loguru import logger
import igl
import json
import yaml

from config import PathCofig
from pygarment.meshgen.box_mesh_gen import BoxMesh
from pygarment.meshgen.pattern_data import PatternData, SimulationConfig
from pygarment.meshgen.simulation import run_sim
from pygarment.meshgen.garment_data import GarmentData
import pygarment.meshgen.box_mesh_gen as bmg



def batch_sim_with_data(
    pattern_data: dict[str, PatternData],
    sim_config: SimulationConfig,
    run_default_body: bool = False,
    num_samples: Optional[int] = None,
    caching: bool = False
) -> bool:
    """Perform pattern simulation using in-memory pattern data.
    
    Uses pattern data passed directly instead of reading from disk. Data is still
    saved to disk for backup, but simulation uses the in-memory structures for
    improved performance.
    
    Parameters
    ----------
    pattern_data : dict[str, PatternData]
        Dictionary mapping pattern names to PatternData objects.
        Each PatternData contains piece, body_params, body_def, design, 
        attachment_constraints, and paths.
    sim_config : SimulationConfig
        Simulation configuration object with SimConfig and RenderConfig.
    run_default_body : bool, optional
        If True, runs the dataset on the default body. Default is False.
    num_samples : int, optional
        Number of samples to process in this batch. If None, processes all samples.
        Default is None.
    caching : bool, optional
        If True, enables caching of every frame of simulation. This significantly
        slows down simulation. Default is False.

    Returns
    -------
    bool
        True if all samples were processed successfully, False otherwise.
    """
    body_type = 'default_body' if run_default_body else 'random_body'
    
    # Get output path from first pattern's PathCofig
    if not pattern_data:
        logger.error("No pattern data provided")
        return False
    first_pattern = next(iter(pattern_data.values()))
    if not isinstance(first_pattern, PatternData):
        logger.error("Pattern data must contain PatternData objects")
        return False
    
    # Get pattern names from in-memory data
    pattern_names = list(pattern_data.keys())
    total_patterns = len(pattern_names)
    logger.info(f"Starting batch simulation with in-memory data: {total_patterns} patterns found (body_type: {body_type})")
    if num_samples is not None:
        logger.info(f"Processing {num_samples} samples in this batch")

    # Simulate every template
    count = 0
    for pattern_name in pattern_names:
        try:
            # Use in-memory pattern data (includes PathCofig)
            pattern_info = pattern_data[pattern_name]
            if not isinstance(pattern_info, PatternData):
                logger.error(f"Pattern {pattern_name} is not a PatternData object")
                continue
            
            template_simulation_with_data(
                pattern_info.paths, 
                sim_config,
                pattern_info.piece,
                pattern_info.body_params,
                pattern_info.body_def,
                pattern_info.design,
                caching=caching,
                attachment_constraints=pattern_info.attachment_constraints
            )
        except BaseException as e: 
            logger.error(f"Pattern simulation failed for {pattern_name}: {e}")
            logger.exception("Exception details:")

        count += 1
        
        # Log progress periodically
        if count % 10 == 0:
            logger.info(f'Processed {count} patterns...')
        
        if num_samples is not None and count >= num_samples:
            logger.info(f"Batch limit reached ({num_samples} samples processed)")
            break

    logger.info(f'Finished batch processing: {count}/{total_patterns} patterns processed.')
    return count == total_patterns


def template_simulation_with_data(
    paths: PathCofig,
    sim_config: SimulationConfig,
    piece: Any,
    body_params: Any,
    body_def: Any,
    design: dict[str, Any],
    caching: bool = False,
    attachment_constraints: list[Any] | None = None
) -> None:
    """Simulate a garment template using in-memory pattern data.
    
    This function uses pattern data passed directly instead of reading from disk.
    The data is still saved to disk for backup, but simulation uses the
    in-memory structures for improved performance.
    
    Parameters
    ----------
    paths : PathCofig
        Path configuration object containing all necessary file paths.
    sim_config : SimulationConfig
        Simulation configuration object with SimConfig and RenderConfig.
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
        
    Raises
    ------
    TimeoutError
        If mesh generation takes longer than the configured timeout.
    PatternLoadingError
        If the pattern cannot be loaded correctly.
    BaseException
        If any other error occurs during pattern loading or simulation.
    """
    
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
        with open(design_params_path, 'w') as f:
            yaml.dump({'design': design}, f, default_flow_style=False, sort_keys=False)
    
    # Use SimConfig from sim_config
    config = sim_config.sim_config
    res = config.resolution_scale
    
    garment_box_mesh = BoxMesh(spec_path, res)
    
    # Load BoxMesh with timeout handling
    timeout_after = int(config._props.get('max_meshgen_time', 20))
    
    try:
        _load_boxmesh_timeout(garment_box_mesh, timeout_after)
    except TimeoutError as e:
        logger.error(f"Mesh generation timeout for {garment_box_mesh.name}: {e}")
        return
    except bmg.PatternLoadingError as e:
        logger.error(f"Pattern loading error for {garment_box_mesh.name}: {e}")
        return
    except BaseException as e:
        logger.error(f"Pattern loading failed for {garment_box_mesh.name}: {e}")
        logger.exception("Exception details:")
        return
    
    # Process attachment constraints using callback
    # The callback gets constraints internally from the garment program
    vertex_processor = piece.get_vertex_processor_callback()  # type: ignore[attr-defined]
    if vertex_processor is not None:
        garment_box_mesh.process_attachment_constraints(vertex_processor)
        logger.debug(
            f"Processed attachment constraints for {garment_box_mesh.name} "
            f"({len(garment_box_mesh.attachment_constraints)} constraints)"
        )
    
    # Serialize BoxMesh (for backup and rendering)
    options_dict = config._props.get('options', {})
    vertex_normals = options_dict.get('store_vertex_normals', False)
    store_panels = options_dict.get('store_panels', False)
    
    # Use render config from sim_config
    render_config = sim_config.render_config
    
    garment_box_mesh.serialize(
        paths, 
        with_v_norms=vertex_normals, 
        store_panels=store_panels,
        uv_config=render_config.uv_texture.model_dump()
    )
    
    # Load body mesh data
    body_vertices, body_faces = igl.read_triangle_mesh(str(paths.in_body_obj))
    body_indices = body_faces.flatten()
    
    # Load body segmentation
    with open(paths.body_seg, 'r') as f:
        body_segmentation = json.load(f)
    
    # Extract vertex labels from BoxMesh (if available)
    vertex_labels = (
        garment_box_mesh.vertex_labels 
        if hasattr(garment_box_mesh, 'vertex_labels') and garment_box_mesh.vertex_labels 
        else None
    )
    
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
    
    # Update config dict with attachment constraints from BoxMesh for run_sim compatibility
    if garment_box_mesh.attachment_constraints:
        constraints_dicts = [c.model_dump() for c in garment_box_mesh.attachment_constraints]
        
        # Update the options dict
        if 'options' not in config._props:
            config._props['options'] = {}
        config._props['options']['attachment_constraints'] = constraints_dicts
        config._props['options']['enable_attachment_constraint'] = True
    
    # Create dict for run_sim compatibility
    sim_dict = {
        'sim': {
            'config': config._props,
            'stats': {}
        },
        'render': {
            'config': render_config.model_dump(),
            'stats': {}
        }
    }
    
    # Run simulation
    logger.debug(f'Running simulation for {garment_box_mesh.name} with in-memory data...')
    optimize_storage = config._props.get('optimize_storage', False)
    
    run_sim(
        garment_box_mesh.name,  
        sim_dict,
        paths,
        save_v_norms=vertex_normals,
        store_usd=caching,
        optimize_storage=optimize_storage,
        verbose=False,
        garment_data=garment_data
    )


def _load_boxmesh_timeout(garment: BoxMesh, timeout_after: int) -> None:
    """Load boxmesh with timeout protection.
    
    Parameters
    ----------
    garment : BoxMesh
        Garment mesh to load.
    timeout_after : int
        Timeout in seconds.
        
    Raises
    ------
    TimeoutError
        If loading exceeds the timeout.
    """
    if platform.system() == "Windows":
        # Windows timeout using multiprocessing
        def load_garment() -> None:
            garment.load()
        
        p = multiprocessing.Process(target=load_garment, name="GarmentGeneration")
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
        def alarm_handler(signum: int, frame: Any) -> None:
            raise TimeoutError(f"Garment loading exceeded timeout of {timeout_after}s")

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout_after)
        try:
            garment.load()
        except TimeoutError:
            raise
        finally:
            signal.alarm(0)
