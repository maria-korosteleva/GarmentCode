# Copyright (c) 2022 NVIDIA CORPORATION.  All rights reserved.
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

###########################################################################
# Example Sim Cloth
#
# Shows a simulation of an FEM cloth model colliding against a static
# rigid body mesh using the wp.sim.ModelBuilder().
#
###########################################################################

import sys
import time
import traceback
import platform
import multiprocessing
import signal
import trimesh

# Warp
import warp as wp

# Custom code
from pygarment.meshgen.render.pythonrender import render_images
from pygarment.meshgen.garment import Cloth
from pygarment.meshgen.sim_config import SimConfig, PathCofig

wp.init()

class SimulationError(BaseException):
    """To be rised when panel stitching cannot be executed correctly"""
    pass

class FrameTimeOutError(BaseException):
    """To be rised when frame takes too long to simulate"""
    pass

class SimTimeOutError(BaseException):
    """To be rised when simulation takes too long"""
    pass

def optimize_garment_storage(paths: PathCofig):
    """Prepare the data element for compact storage: store the meshes as ply instead of obj, 
        remove texture files 
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


def update_progress(progress, total):
    """Progress bar in console"""
    # https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    amtDone = progress / total
    num_dash = int(amtDone * 50)
    sys.stdout.write('\rProgress: [{0:50s}] {1:.1f}%'.format('#' * num_dash + '-' * (50 - num_dash), amtDone * 100))
    sys.stdout.flush()

def _run_frame_with_timeout(garment, frame_timeout, frame_num):
    """Run frame while keeping a cap on time to run it"""
    try:
        if platform.system() == "Windows":
            """https://stackoverflow.com/a/14920854"""

            if frame_num == 0: #only do it on first frame due to slowdown
                p_frame = multiprocessing.Process(target=garment.run_frame(), name="FrameSimulation")
                p_frame.start()

                # Wait timeout_after seconds for garment.run_frame()
                p_frame.join(frame_timeout)

                # If thread is active
                if p_frame.is_alive():
                    # Terminate the process
                    p_frame.terminate()
                    p_frame.join()
                    raise TimeoutError
            else:
                garment.run_frame()

        elif platform.system() in ["Linux", "OSX"]:
            """https://code-maven.com/python-timeout"""

            def alarm_handler(signum, frame):
                raise TimeoutError

            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(frame_timeout)
            try:
                garment.run_frame()
            except TimeoutError as ex:
                raise TimeoutError
            else:
                signal.alarm(0)

    except TimeoutError as e:
        raise FrameTimeOutError

def sim_frame_sequence(garment, config, store_usd=False, verbose=False):

    # Save initial state
    if store_usd:
        garment.render_usd_frame()

    start_time = time.time()
    for frame in range(0, config.max_sim_steps):
        
        if verbose:
            print(f'\n------ Frame {frame + 1} ------')
        else:
            update_progress(frame, config.max_sim_steps)

        garment.frame = frame 

        #Run frame and raise FrameTimeOutError if frame takes too long to simulate

        static = False
        if config.max_frame_time is None:
            # No frame time limits
            garment.run_frame()
        else:
            # NOTE: frame timeouts only work in the main thread of the program. 
            # disable frame timeout by passing 'null' as a max_frame_time parameter in config
            _run_frame_with_timeout(
                garment, 
                frame_timeout=config.max_frame_time if frame > 0 else config.max_frame_time * 2,
                frame_num=frame
            )

        if verbose:
            num_cloth_cloth_contacts = garment.count_self_intersections()
            print(f'\nSelf-Intersection: {num_cloth_cloth_contacts}')

        if frame >= config.zero_gravity_steps and frame >= config.min_sim_steps:
            static, _ = garment.is_static()
        if static:
            break

        runtime = time.time() - start_time
        if runtime > config.max_sim_time:
            raise SimTimeOutError
        

def run_sim(
        cloth_name, props, paths: PathCofig, 
        save_v_norms=False, store_usd=False, 
        optimize_storage=False,
        verbose=False): 
    """Initialize and run the simulation
    !! Important !! 
        'store_usd' parameter slows down the simulation to CPU rates because of required CPU-GPU copies and file writes. Use only for debugging
    """
    sim_props = props['sim']
    render_props = props['render']

    start_time = time.time()

    config = SimConfig(sim_props['config'])   # Why separate class at all? 
    garment = Cloth(cloth_name, config, paths, caching=store_usd)

    try:
        print("Simulation..")
        sim_frame_sequence(garment, config, store_usd, verbose=verbose)
    
    except FrameTimeOutError:
        print(f"FrameTimeOutError at frame {garment.frame}")
        props.add_fail('sim', 'frame_timeout', cloth_name)
    except SimTimeOutError:
        print("SimTimeOutError")
        props.add_fail('sim', 'simulation_timeout', cloth_name)
    except SimulationError:
        print("Simulation failed")
        props.add_fail('sim', 'gt_edges_creation', cloth_name)
    except BaseException as e:
        print(f'Sim::{cloth_name}::crashed with {e}')

        if isinstance(e, KeyboardInterrupt):
            # Allow to stop simulation loops by keyboard interrupt
            # It's not a real crash, so don't write down the failure
            sec = round(time.time() - start_time, 3)
            min = int(sec / 60)
            print(f"Simulation pipeline took: {min} m {sec - min * 60} s")
            raise e

        traceback.print_exc()
        props.add_fail('sim', 'crashes', cloth_name)
    else:  # Other quality checks
        if garment.frame == config.max_sim_steps - 1:
            _, non_st_count = garment.is_static()
            print('\nFailed to achieve static equilibrium for {} with {} non-static vertices out of {}'.format(
                cloth_name, non_st_count, len(garment.current_verts)))
            props.add_fail('sim', 'static_equilibrium', cloth_name)

        if time.time() - start_time < 0.5:  # 0.5 sec  -- finished suspiciously fast
            props.add_fail('sim', 'fast_finish', cloth_name)

        # 3D penetrations
        num_body_collisions = garment.count_body_intersections()
        print("BODY CLOTH INTERSECTIONS: ", num_body_collisions)
        num_self_collisions = garment.count_self_intersections()

        sim_props['stats']['body_collisions'][cloth_name] = num_body_collisions
        sim_props['stats']['self_collisions'][cloth_name] = num_self_collisions

        if num_body_collisions > config.max_body_collisions:
            props.add_fail('sim', 'cloth_body_intersection', cloth_name)
        if num_self_collisions: 
            print(f'Self-Intersecting with {num_self_collisions}, '
                  f'is fail: {num_self_collisions > config.max_self_collisions}')
            if num_self_collisions > config.max_self_collisions:
                props.add_fail('sim', 'cloth_self_intersection', cloth_name)
        else:
            print('Not self-intersecting!!!')

    # ---- Postprocessing ----
    # NOTE: Attempt even on failures for accurate picture and post-analysis
    frame = garment.frame
    print(f"\nSimulation took #frames={frame + 1}")

    sim_props['stats']['sim_time'][cloth_name] = sim_time = time.time() - start_time
    sim_props['stats']['spf'][cloth_name] = sim_time / frame if frame else sim_time
    sim_props['stats']['fin_frame'][cloth_name] = frame

    garment.save_frame(save_v_norms=save_v_norms) #saving after stats

    # Render images
    s_time = time.time()
    render_images(paths, garment.v_body, garment.f_body, render_props['config'])
    render_image_time = time.time() - s_time
    render_props['stats']['render_time'][cloth_name] = render_image_time  
    print(f"Rendering {cloth_name} took {render_image_time}s")

    if optimize_storage:
        optimize_garment_storage(paths)

    # Final info output
    sec = round(time.time() - start_time, 3)
    min = int(sec / 60)
    print(f"\nSimulation pipeline took: {min} m {sec - min * 60} s")
