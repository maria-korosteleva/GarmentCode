"""Routines to run cloth simulation in Maya + Qualoth"""

# Basic
import time
import os

# Maya
from maya import cmds

# My modules
from pattern.core import BasicPattern
import mayaqltools as mymaya
from mayaqltools import qualothwrapper as qw


# ----------- High-level requests --------------
def single_file_sim(resources, props, caching=False):
    """
        Simulates the given template and puts the results in original template folder, 
        including config and statistics
    """
    try:
        # ----- Init -----
        init_sim_props(props, True)
        qw.load_plugin()
        scene = mymaya.Scene(
            os.path.join(resources['bodies_path'], props['body']),
            props['render'], 
            scenes_path=resources['scenes_path'])

        # Main part
        template_simulation(os.path.join(resources['templates_path'], props['templates']), 
                            scene, props['sim'], caching=caching)

        # Fin
        print('\nFinished experiment')
        try:
            # remove unnecessaty field
            del props['sim']['stats']['processed']
        except KeyError:
            pass
        props.serialize(os.path.join(resources['templates_path'], 'props.json'))
    except Exception as e:
        print(e)


def batch_sim(resources, data_path, dataset_props, 
              num_samples=None, caching=False, force_restart=False):
    """
        Performs pattern simulation for each example in the dataset 
        given by dataset_props. 
        Batch processing is automatically resumed 
        from the last unporcessed datapoint if restart is not forced. The last 
        example on the processes list is assumed to cause the failure, so it can be later found in failure cases. 

        Parameters:
            * resources -- dict of paths to needed resoursed: 
                * body_path -- path to folder with body meshes
                * data_path -- path to folder with the dataset
                * scenes_path -- path to folder with rendering scenes
            * dataset_props -- dataset properties. Properties has to be of custom customconfig.Properties() class and contain
                    * dataset folder (inside data_path) 
                    * name of pattern template
                    * name of body .obj file
                    * type of dataset structure (with/without subfolders for patterns)
                    * list of processed samples if processing of dataset was allready attempted
                Other needed properties will be filles with default values if the corresponding sections
                are not found in props object
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

    qw.load_plugin()
    scene = mymaya.Scene(
        os.path.join(resources['bodies_path'], dataset_props['body']),
        dataset_props['render'], 
        scenes_path=resources['scenes_path'])
    
    pattern_specs = _get_pattern_files(data_path, dataset_props)
    data_props_file = os.path.join(data_path, 'dataset_properties.json')

    # Simulate every template
    count = 0
    for pattern_spec in pattern_specs:
        # skip processed cases -- in case of resume. First condition needed to skip checking second one on False =) 
        pattern_spec_norm = os.path.normpath(pattern_spec)
        pattern_name = BasicPattern.name_from_path(pattern_spec_norm)
        if resume and pattern_name in dataset_props['sim']['stats']['processed']:
            print('Skipped as already processed {}'.format(pattern_spec_norm))
            continue

        dataset_props['sim']['stats']['processed'].append(pattern_name)
        _serialize_props_with_sim_stats(dataset_props, data_props_file)  # save info of processed files before potential crash

        template_simulation(pattern_spec_norm, 
                            scene, 
                            dataset_props['sim'], 
                            delete_on_clean=True,  # delete geometry after sim as we don't need it any more
                            caching=caching, 
                            save_maya_scene=False)
        
        if pattern_name in dataset_props['sim']['stats']['fails']['crashes']:
            # if we successfully finished simulating crashed example -- it's not a crash any more!
            print('Crash successfully resimulated!')
            dataset_props['sim']['stats']['fails']['crashes'].remove(pattern_name)

        count += 1  # count actively processed cases
        if num_samples is not None and count >= num_samples:  # only process requested number of samples       
            break

    # Fin
    print('\nFinished batch of ' + os.path.basename(data_path))
    try:
        if len(dataset_props['sim']['stats']['processed']) >= len(pattern_specs):
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


# ------- Utils -------
def init_sim_props(props, batch_run=False, force_restart=False):
    """ 
        Add default config values if not given in props & clean-up stats if not resuming previous processing
        Returns a flag wheter current simulation is a resumed last one
    """
    if 'sim' not in props:
        props.set_section_config(
            'sim', 
            max_sim_steps=500, 
            zero_gravity_steps=5,  # time to assembly 
            static_threshold=0.05,  # 0.01  # depends on the units used, 
            non_static_percent=1,
            material={},
            body_friction=0.5, 
            resolution_scale=5
        )
    
    if 'material' not in props['sim']['config']:
        props['sim']['config']['material'] = {}

    if 'render' not in props:
        # init with defaults
        props.set_section_config(
            'render',
            resolution=[800, 800]
        )
    
    if batch_run and 'processed' in props['sim']['stats'] and not force_restart:
        # resuming existing batch processing -- do not clean stats 
        # Assuming the last example processed example caused the failure
        last_processed = props['sim']['stats']['processed'][-1]
        props['sim']['stats']['stop_over'].append(last_processed)  # indicate resuming dataset simulation 

        if not any([(name in last_processed) or (last_processed in name) for name in props['render']['stats']['render_time']]):
            # crash detected -- the last example does not appear in the stats
            if last_processed not in props['sim']['stats']['fails']['crashes']:
                # first time to crash here -- try to re-do this example => remove from visited
                props['sim']['stats']['processed'].pop()
                props['sim']['stats']['fails']['crashes'].append(last_processed)
            # else we crashed here before -- do not re-try + leave in crashed list

        return True
    
    # else new life
    # Prepare commulative stats
    props.set_section_stats('sim', fails={}, sim_time={}, spf={}, fin_frame={})
    props['sim']['stats']['fails'] = {
        'crashes': [],
        'intersect_colliders': [],
        'intersect_self': [],
        'static_equilibrium': [],
        'fast_finish': [],
        'pattern_loading': []
    }

    props.set_section_stats('render', render_time={})

    if batch_run:  # track batch processing
        props.set_section_stats('sim', processed=[], stop_over=[])

    return False
        

def template_simulation(spec, scene, sim_props, delete_on_clean=False, caching=False, save_maya_scene=False):
    """
        Simulate given template within given scene & save log files
    """
    print('\nGarment load')
    garment = mymaya.MayaGarment(spec)
    try:
        garment.load(
            shader_group=scene.cloth_SG(), 
            obstacles=[scene.body],  # I don't add floor s.t. garment falls infinitely if falls
            config=sim_props['config']
        )
    except mymaya.PatternLoadingError as e:
        # record error and skip subequent processing
        sim_props['stats']['fails']['pattern_loading'].append(garment.name)
    else:
        # garment.save_mesh(tag='stitched')  # Saving the geometry before eny forces were applied
        garment.sim_caching(caching)

        qw.run_sim(garment, sim_props)

        # save even if sim failed -- to see what happened!
        garment.save_mesh(tag='sim')
        scene.render(garment.path, garment.name)
        if save_maya_scene:
            # save current Maya scene
            cmds.file(rename=os.path.join(garment.path, garment.name + '_scene'))
            cmds.file(save=True, type='mayaBinary', force=True, defaultExtensions=True)

        garment.clean(delete_on_clean)


def _serialize_props_with_sim_stats(dataset_props, filename):
    """Compute data processing statistics and serialize props to file"""
    dataset_props.stats_summary()
    dataset_props.serialize(filename)


def _get_pattern_files(data_path, dataset_props):
    """ Collects paths to all the pattern files in given folder"""

    to_ignore = ['renders']  # special dirs not to include in the pattern list

    pattern_specs = []
    root, dirs, files = next(os.walk(data_path))
    if dataset_props['to_subfolders']:
        # https://stackoverflow.com/questions/800197/how-to-get-all-of-the-immediate-subdirectories-in-python
        for directory in dirs:
            if directory not in to_ignore:
                pattern_specs.append(os.path.join(root, directory, 'specification.json'))  # cereful for file name changes ^^
    else:
        for file in files:
            # NOTE filtering might not be very robust
            if ('.json' in file
                    and 'specification' in file
                    and 'template' not in file):
                pattern_specs.append(os.path.normpath(os.path.join(root, file)))
    return pattern_specs

