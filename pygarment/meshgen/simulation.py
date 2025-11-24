import sys
import time
import traceback
import trimesh
from typing import Optional, Any

# Warp
import warp as wp

# Logging
from loguru import logger

# Custom code
from pygarment.meshgen.render.pythonrender import render_images
from pygarment.meshgen.garment import SimulationGarment
from pygarment.meshgen.garment_data import GarmentData
from config import PathCofig
from config.sim_config import SimConfig
from config.dataset_properties import DatasetProperties

wp.init()

class SimulationError(BaseException):
    """Exception raised when panel stitching cannot be executed correctly."""
    pass


def optimize_garment_storage(paths: PathCofig) -> None:
    """Prepare the data element for compact storage.
    
    Converts OBJ meshes to PLY format and removes texture files to reduce storage size.
    
    Parameters
    ----------
    paths : PathCofig
        Path configuration object containing paths to garment mesh files.
        
    Note
    ----
    This function silently handles any errors during conversion, continuing with
    the next file if one fails.
    """
    # Objs to ply
    try:
        boxmesh = trimesh.load(paths.g_box_mesh)
        boxmesh.export(paths.g_box_mesh_compressed)
        paths.g_box_mesh.unlink()
    except BaseException:
        pass

    try:
        simmesh = trimesh.load(paths.g_sim)
        simmesh.export(paths.g_sim_compressed)
        paths.g_sim.unlink()
    except BaseException:
        pass

    # Remove large texture file and mtl -- not so necessary
    paths.g_texture_fabric.unlink(missing_ok=True)
    paths.g_mtl.unlink(missing_ok=True)


def update_progress(progress: int, total: int) -> None:
    """Display a progress bar in the console.
    
    Parameters
    ----------
    progress : int
        Current progress value (number of completed items).
    total : int
        Total number of items to process.
    """
    amtDone = progress / total
    num_dash = int(amtDone * 50)
    sys.stdout.write('\rProgress: [{0:50s}] {1:.1f}%'.format('#' * num_dash + '-' * (50 - num_dash), amtDone * 100))
    sys.stdout.flush()


def sim_frame_sequence(
    garment: SimulationGarment,
    config: SimConfig,
    store_usd: bool = False,
    verbose: bool = False
) -> None:
    """Run the simulation frame sequence.
    
    Executes the simulation for the specified number of frames, checking for
    static equilibrium after the minimum number of steps and zero gravity steps.
    
    Parameters
    ----------
    garment : SimulationGarment
        The garment simulation object to run frames on.
    config : SimConfig
        Simulation configuration containing frame limits and step counts.
    store_usd : bool, optional
        Whether to store USD frames. If True, saves the initial state as USD.
        Default is False.
    verbose : bool, optional
        Whether to print verbose output including frame-by-frame information
        and self-intersection counts. Default is False.
        
    Note
    ----
    The simulation will stop early if static equilibrium is achieved after
    both `zero_gravity_steps` and `min_sim_steps` have been completed.
    """
    # Save initial state
    if store_usd:
        garment.render_usd_frame()

    for frame in range(0, config.max_sim_steps):
        if verbose:
            logger.info(f'\n------ Frame {frame + 1} ------')
        else:
            update_progress(frame, config.max_sim_steps)

        garment.frame = frame
        garment.run_frame()

        if verbose:
            num_cloth_cloth_contacts = garment.count_self_intersections()
            logger.debug(f'\nSelf-Intersection: {num_cloth_cloth_contacts}')

        if frame >= config.zero_gravity_steps and frame >= config.min_sim_steps:
            static, _ = garment.is_static()
            if static:
                break
        

def run_sim(
    cloth_name: str,
    props: dict[str, Any],
    paths: PathCofig,
    save_v_norms: bool = False,
    store_usd: bool = False,
    optimize_storage: bool = False,
    verbose: bool = False,
    garment_data: Optional[GarmentData] = None
) -> None:
    """Initialize and run the simulation.
    
    This function sets up the simulation environment, runs the frame sequence,
    performs quality checks, saves the results, and optionally renders images.
    
    Parameters
    ----------
    cloth_name : str
        Name of the cloth/garment being simulated.
    props : Any
        Properties object (dict-like) containing simulation and render properties.
        Will be converted to DatasetProperties internally. Must have keys:
        - 'sim': Dictionary with simulation configuration and stats
        - 'render': Dictionary with rendering configuration and stats
    paths : PathCofig
        Path configuration object containing all necessary file paths.
    save_v_norms : bool, optional
        Whether to save vertex normals in the output mesh. Default is False.
    store_usd : bool, optional
        Whether to store USD frames. Slows down simulation significantly
        due to CPU-GPU copies and file writes. Use only for debugging.
        Default is False.
    optimize_storage : bool, optional
        Whether to optimize storage by converting OBJ files to PLY format
        and removing texture files. Default is False.
    verbose : bool, optional
        Whether to print verbose output during simulation. Default is False.
    garment_data : GarmentData, optional
        Optional in-memory garment data. If provided, the simulation will
        use this data directly instead of reading from disk. This improves
        performance by avoiding redundant I/O operations. Default is None
        (read from disk).
        
    Raises
    ------
    SimulationError
        If the simulation fails due to a known error condition.
    BaseException
        If the simulation crashes due to an unexpected error.
        
    Note
    ----
    After simulation, quality checks are performed and logged as warnings
    if issues are detected. The simulation continues regardless of quality
    check results.
    """
    start_time = time.time()

    # Use DatasetProperties class instead of dictionary access
    dataset_props = DatasetProperties.from_props(props)
    config = dataset_props.sim.get_sim_config()
    garment = SimulationGarment(cloth_name, config, paths, caching=store_usd, garment_data=garment_data)

    try:
        logger.info("Simulation..")
        sim_frame_sequence(garment, config, store_usd, verbose=verbose)
    except SimulationError as e:
        logger.error(f"Simulation failed for {cloth_name}: {e}")
        traceback.print_exc()
        raise
    except BaseException as e:
        logger.error(f'Simulation crashed for {cloth_name}: {e}')
        traceback.print_exc()
        raise

    # Quality checks (log warnings and continue)
    frame = garment.frame
    logger.info(f"\nSimulation took #frames={frame + 1}")

    if garment.frame == config.max_sim_steps - 1:
        _, non_st_count = garment.is_static()
        logger.warning(f'Failed to achieve static equilibrium for {cloth_name} with {non_st_count} non-static vertices out of {len(garment.current_verts)}')

    if time.time() - start_time < 0.5:  # 0.5 sec -- finished suspiciously fast
        logger.warning(f'Simulation finished suspiciously fast for {cloth_name} (< 0.5s)')

    # 3D penetrations
    num_body_collisions = garment.count_body_intersections()
    logger.info(f"Body-Cloth Intersections: {num_body_collisions}")
    num_self_collisions = garment.count_self_intersections()

    if num_body_collisions > config.max_body_collisions:
        logger.warning(f'Excessive body-cloth intersections for {cloth_name}: {num_body_collisions} > {config.max_body_collisions}')
    
    if num_self_collisions:
        logger.info(f'Self-Intersecting with {num_self_collisions}')
        if num_self_collisions > config.max_self_collisions:
            logger.warning(f'Excessive self-intersections for {cloth_name}: {num_self_collisions} > {config.max_self_collisions}')
    else:
        logger.info('Mesh is intersection-free')

    garment.save_frame(save_v_norms=save_v_norms)

    # Render images
    render_images(paths, garment.v_body, garment.f_body, dataset_props.render.config)

    if optimize_storage:
        optimize_garment_storage(paths)

    # Final info output
    sec = round(time.time() - start_time, 3)
    min = int(sec / 60)
    logger.info(f"\nSimulation pipeline took: {min} m {sec - min * 60} s")
