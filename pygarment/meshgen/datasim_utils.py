"""Routines to run cloth simulation"""

# Basic
import time
import multiprocessing
import platform
import signal
from pathlib import Path

# BoxMeshGen
import pygarment.meshgen.boxmeshgen as bmg
from pygarment.meshgen.boxmeshgen import BoxMesh
from pygarment.meshgen.sim_config import PathCofig

# Warp simulation
from pygarment.meshgen.simulation import run_sim


def batch_sim(data_path, output_path, dataset_props,
              run_default_body=False, num_samples=None, caching=False, force_restart=False):
    """
        Performs pattern simulation for each example in the dataset
        given by dataset_props.
        Batch processing is automatically resumed
        from the last unporcessed datapoint if restart is not forced. The last
        example on the processes list is assumed to cause the failure, so it can be later found in failure cases.

        Parameters:
            * data_path -- path to folder with patterns (for given body type)
            * output_path -- path to folder with the sumulated dataset
            * dataset_props -- dataset properties. Properties has to be of custom data_config.Properties() class and contain
                    * dataset folder (inside data_path)
                    * type of dataset structure (with/without subfolders for patterns)
                    * list of processed samples if processing of dataset was already attempted
                    * Simulation parameters
                    * Rendering parameters
                Other needed properties will be files with default values if the corresponding sections
                are not found in props object
            * run_default_body -- runs the dataset on the default body (disabled by default)
            * num_samples -- number of (unprocessed) samples from dataset to process with this run. If None, runs over all unprocessed samples
            * caching -- enables caching of every frame of simulation (disabled by default)
            * force_restart -- force restarting the batch processing even if resume conditions are met.

    """
    # ----- Init -----
    if 'frozen' in dataset_props and dataset_props['frozen']:
        # avoid accidential re-runs of data
        print('Warning: dataset is frozen, processing is skipped')
        return True

    resume = init_sim_props(dataset_props, batch_run=True, force_restart=force_restart)
    body_type = 'default_body' if run_default_body else 'random_body'
    data_props_file = output_path / f'dataset_properties_{body_type}.yaml'
    pattern_names = _get_pattern_names(data_path)

    # Simulate every template
    count = 0
    for pattern_name in pattern_names:
        # skip processed cases -- in case of resume. First condition needed to skip checking second one on False =)
        if resume and pattern_name in dataset_props['sim']['stats']['processed']:
            print(f'Skipped as already processed {pattern_name}')
            continue

        dataset_props['sim']['stats']['processed'].append(pattern_name)
        _serialize_props_with_sim_stats(dataset_props,
                                        data_props_file)  # save info of processed files before potential crash

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
            print("***Pattern loading failed (paths)***")
            dataset_props.add_fail('sim', 'crashes', pattern_name)
        else:
            template_simulation(paths, dataset_props, caching=caching)

        count += 1  # count actively processed cases
        if num_samples is not None and count >= num_samples:  # only process requested number of samples
            break

    # Fin
    print(f'\nFinished batch of {data_path}')  
    try:
        if len(dataset_props['sim']['stats']['processed']) >= len(pattern_names):
            # processing successfully finished -- no need to resume later
            del dataset_props['sim']['stats']['processed']
            dataset_props['frozen'] = True
            process_finished = True
        else:
            process_finished = False
    except KeyError:
        print('KeyError -processed-')
        process_finished = True
        pass

    # Logs
    _serialize_props_with_sim_stats(dataset_props, data_props_file)

    return process_finished


def resim_fails(data_path, output_path, dataset_props,
              run_default_body=False, caching=False):
    """Resimulate failure cases -- maybe some of them would get fixed"""

    print('************** RESIMULATING FAILS ****************')

    sim_stats = dataset_props['sim']['stats']
    
    # Collect fails and remove them from fails list if any
    fails = sim_stats['fails']
    to_resim = set()
    for key in fails:
        if key not in ['cloth_body_intersection', 'cloth_self_intersection']:
            for el in fails[key]:
                to_resim.add(el)
            fails[key] = []   # NOTE: If nothing to be added in this key, it was already an empty array (and nothing changed)
    
    if not len(to_resim):
        # Return previous finished state
        return dataset_props['frozen'] if 'frozen' in dataset_props else False
    
    if 'processed' not in sim_stats:
        sim_stats['processed'] = _get_pattern_names(data_path)
    dataset_props['frozen'] = False

    # Remove fails from processed to trigger re-simulation
    for sample in to_resim:
        sim_stats['processed'].remove(sample)

    # Start simulation again
    finished = batch_sim(
        data_path, output_path, dataset_props, 
        run_default_body=run_default_body, 
        num_samples=len(to_resim)+1, 
        caching=caching, 
        force_restart=False
    )

    return finished

# ------- Utils -------
def init_sim_props(props, batch_run=False, force_restart=False):
    """
        Add default config values if not given in props & clean-up stats if not resuming previous processing
        Returns a flag whether current simulation is a resumed last one
    """
    if 'sim' not in props:
        props.set_section_config(
            'sim',
            max_sim_steps=1000, #affects speed
            max_meshgen_time=20, #in seconds, affects speed
            max_frame_time= 15, #in seconds, affects speed
            max_sim_time= 1500, #in seconds, affects speed
            zero_gravity_steps=10,  # 0.01  # depends on the units used, #affects speed
            static_threshold=0.03, #affects speed
            non_static_percent=1.5, #affects speed
            max_body_collisions=0,
            max_self_collisions=0,
            resolution_scale=1.0, #affects speed
            ground=False, # Do not add floor s.t. garment falls infinitely if falls
        )

    if 'material' not in props['sim']['config']:
        props['sim']['config']['material'] = {  
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

    if 'options' not in props['sim']['config']:
        props['sim']['config']['options'] = {
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

            # FIXME Re-writes mesh references causing occasional CUDA errors when referencing meshes other than the body
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
        # resuming existing batch processing -- do not clean stats
        # Assuming the last example processed example caused the failure
        last_processed = props['sim']['stats']['processed'][-1]

        if not any([(name in last_processed) or (last_processed in name) for name in
                    props['render']['stats']['render_time']]):
            # crash detected -- the last example does not appear in the stats
            if last_processed not in props['sim']['stats']['fails']['crashes']:
                # add to simulation failures
                # Remove last from processed if it did not crash
                if last_processed not in props['sim']['stats']['stop_over']:   
                    props['sim']['stats']['processed'].pop()
                else:
                    # Already passed here once -> add as crash
                    props['sim']['stats']['fails']['crashes'].append(last_processed)

        props['sim']['stats']['stop_over'].append(last_processed)  # indicate resuming dataset simulation


        return True

    # else new life
    # Prepare commulative stats
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

    return False


def template_simulation(paths: PathCofig, props, caching=False):
    """
        Simulate given template within given scene & save log files
    """
    sim_props = props['sim']
    res = sim_props['config']['resolution_scale']

    garment = BoxMesh(paths.in_g_spec, res)

    print('\n-----------------------------'
          '\nLoading garment: ', garment.name)

    meshgen_start_time = time.time()
    timeout_after = int(get_dict_default_value(sim_props['config'], 'max_meshgen_time', 20))

    try:
        _load_boxmesh_timeout(garment, timeout_after)
    except TimeoutError as e:
        print(e)
        failure_case = 'meshgen-timeout'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.PatternLoadingError as e:
        # record error and skip subequent processing
        print(e)
        failure_case = 'pattern_loading'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.DegenerateTrianglesError as e:
        print(e)
        failure_case = 'degenerate_triangles'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.MultiStitchingError as e:
        print(e)
        failure_case = 'multi_stitching'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.NormError as e:
        print(e)
        failure_case = 'norm_error'
        props.add_fail('sim', failure_case, garment.name)
    except bmg.StitchingError as e:
        print(e)
        failure_case = 'stitching_error'
        props.add_fail('sim', failure_case, garment.name)
    except BaseException as e:   # Catch the rest of exceptions
        print("***Pattern loading failed due to unknown error***")
        print(e)
        failure_case = 'crashes'
        props.add_fail('sim', failure_case, garment.name)
    else:
        # garment.save_mesh(tag='stitched')  # Saving the geometry before eny forces were applied
        sim_props['stats']['meshgen_time'][garment.name] = time.time() - meshgen_start_time
        sim_props['stats']['face_count'][garment.name] = len(garment.faces)
        sim_props_option = sim_props['config']['options']
        
        vertex_normals = get_dict_default_value(sim_props_option,'store_vertex_normals',False)
        store_panels = get_dict_default_value(sim_props_option,'store_panels',False)
        garment.serialize(
            paths, 
            with_v_norms=vertex_normals, 
            store_panels=store_panels,
            uv_config=props['render']['config']['uv_texture']
        )

        run_sim(
            garment.name,  
            props, 
            paths,
            save_v_norms=vertex_normals,
            store_usd=caching,  # NOTE: False for fast simulation!, 
            optimize_storage=sim_props['config']['optimize_storage'],
            verbose=False
        )

def _load_boxmesh_timeout(garment, timeout_after):
    if platform.system() == "Windows":
        """https://stackoverflow.com/a/14920854"""
        p = multiprocessing.Process(target=garment.load(), name="GarmentGeneration")
        p.start()

        # Wait timeout_after seconds for garment.load()
        time.sleep(timeout_after)

        # If thread is active
        if p.is_alive():
            # Terminate the process
            p.terminate()
            p.join()
            raise TimeoutError

    elif platform.system() in ["Linux", "OSX"]:
        """https://code-maven.com/python-timeout"""
        def alarm_handler(signum, frame):
            raise TimeoutError

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout_after)
        s_time = time.time()
        try:
            garment.load()
        except TimeoutError as ex:
            raise TimeoutError
        else:
            e_time = time.time() - s_time
            # print("No timeout error with time: ",e_time)
            signal.alarm(0)


def get_dict_default_value(props, name, default_value):
    if name in props:
        return props[name]
    return default_value

def _serialize_props_with_sim_stats(dataset_props, filename):
    """Compute data processing statistics and serialize props to file"""
    dataset_props.stats_summary()
    dataset_props.serialize(filename)


def _get_pattern_names(data_path: Path):
    names = []
    to_ignore = ['renders']  # special dirs not to include in the pattern list
    for el in data_path.iterdir():
        if el.is_dir() and el.stem not in to_ignore:
            names.append(el.stem)

    return names