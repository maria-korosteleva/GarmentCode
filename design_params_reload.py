"""Update the sewing patterns generated from the existing design parameters
    with an option to only apply the script to failure cases
"""


"""A modified version of the data generation file from here: 
https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/data_generation/datagenerator.py
"""

from datetime import datetime
from pathlib import Path
import yaml
import sys
import shutil 
import time
import random
import string
import traceback
import argparse

sys.path.insert(0, './external/')
sys.path.insert(1, './')

# Custom
from external.customconfig import Properties
from assets.garment_programs.skirt_paneled import *
from assets.garment_programs.tee import *
from assets.garment_programs.godet import *
from assets.garment_programs.bodice import *
from assets.garment_programs.pants import *
from assets.garment_programs.meta_garment import *
from assets.garment_programs.bands import *
from assets.body_measurments.body_params import BodyParameters

import stats_utils

def get_command_args():
    """command line arguments to control the run"""
    # https://stackoverflow.com/questions/40001892/reading-named-command-arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', '-d', nargs='+', help='names of datasets to re-do', type=str, default=None)

    args = parser.parse_args()
    print('Commandline arguments: ', args)

    return args


def _create_data_folder(properties, path=Path(''), unique=True):
    """ Create a new directory to put dataset in 
        & generate appropriate name & update dataset properties
    """
    # NOTE: Not for re-generation
    # if 'data_folder' in properties:  # will this work?
    #     # => regenerating from existing data
    #     properties['name'] = properties['data_folder'] + '_regen'
    #     data_folder = properties['name']
    # else:
    #     data_folder = properties['name']
    data_folder = properties['data_folder']

    # make unique
    if unique:
        data_folder += '_' + datetime.now().strftime('%y%m%d-%H-%M-%S')
    properties['data_folder'] = data_folder
    path_with_dataset = path / data_folder
    path_with_dataset.mkdir(parents=True)

    default_folder = path_with_dataset / 'default_body'
    body_folder = path_with_dataset / 'random_body'

    default_folder.mkdir(parents=True, exist_ok=True)
    body_folder.mkdir(parents=True, exist_ok=True)

    return path_with_dataset, default_folder, body_folder


def body_sample(idx, bodies: dict, path: Path, straight=True):

    body_i = bodies[idx]

    mes_file = body_i['mes']
    obj_file = body_i['objs']['straight'] if straight else body_i['objs']['apart']

    body = BodyParameters(path / mes_file)
    body.params['body_sample'] = (path / obj_file).stem

    return body


def _save_sample(piece, body, new_design, folder, verbose=False):

    pattern = piece.assembly()
    # Save as json file
    folder = pattern.serialize(
        folder, 
        tag='',
        to_subfolder=True,
        with_3d=True, with_text=False, view_ids=False)

    body.save(folder)
    with open(Path(folder) / 'design_params.yaml', 'w') as f:
        yaml.dump(
            {'design': new_design}, 
            f,
            default_flow_style=False,
            sort_keys=False
        )
    if verbose:
        print(f'Saved {piece.name}')
    
    return pattern


def filtered_subfolders(
        datapath, 
        props:Properties, 
        filter_fails=False, 
        only_fails=False,
        fail_types=[], 
        verbose=False
    ):
    """List of the datapoints to reload"""
    sub_paths = list(datapath.iterdir())

    names = []
    for i, el_path in enumerate(sub_paths):
        if el_path.is_file() or 'render' in el_path.name:
            continue
        el_name = el_path.name
        is_fail, section = props.is_fail_section(el_name)

        if (filter_fails and is_fail
                or only_fails and (not is_fail or (section not in fail_types if fail_types else False))):
            continue
        names.append(el_name)

        if verbose:
            print(f'{el_name}: {is_fail}, {section}')


    return names


def generate(
        path, 
        properties: Properties, 
        in_datapath, 
        sys_paths, 
        default_body=True,
        verbose=False, 
        fail_types=[]):
    """Generates a synthetic dataset of patterns with given properties
        Params:
            path : path to folder to put a new dataset into
            props : an instance of DatasetProperties class
                    requested properties of the dataset
    """
    path = Path(path)
    gen_stats = properties['generator']['stats']

    # create data folder
    data_folder, default_path, body_sample_path = _create_data_folder(
        properties, path, 
        unique=False 
    )
    default_sample_data = default_path / 'data'

    if not default_body:
        body_sample_data = body_sample_path / 'data'

    if default_body:
        default_body = BodyParameters(
            Path(sys_paths['bodies_default_path']) / (properties['body_default'] + '.yaml'))
    
    names = filtered_subfolders(
        in_datapath, properties, only_fails=False,
        fail_types=fail_types,
        verbose=verbose
    )

    # Re-create props
    if default_body:
        new_props = Properties()
        new_props.set_basic(
            design_file='./assets/design_params/default.yaml',
            body_default='mean_all',
            body_samples=properties['body_samples'],
            size=properties['size'],
            name=properties['data_folder'],
            data_folder=properties['data_folder'],
            to_subfolders=True)
        new_props.set_section_config(
            'generator', 
            random_seed=properties['generator']['config']['random_seed'],
            generation_time = gen_stats['generation_time']
        )
        
        new_props.set_section_stats(
            'generator',
            panel_count={},
            garment_types={},
            garment_types_summary=dict(main={}, style={})
        )
        gen_stats = new_props['generator']['stats']

    for name in names:
        # Load design from the init folder
        try:
            fname1 = in_datapath / name / f'{name}_design_params.yaml'
            fname2 = in_datapath / name / 'design_params.yaml'
            fname = fname1 if fname1.exists() else fname2
            with open(fname, 'r') as f:
                design = yaml.safe_load(f)['design']
        except FileNotFoundError:
            if verbose:
                print('FileNotFoundError::', fname)
            continue   # Just skip examples without design files

        if default_body: # On default body
            try:
                piece_default = MetaGarment(name, default_body, design) 
                pattern = _save_sample(piece_default, default_body, design, default_sample_data, verbose=verbose)
            except KeyboardInterrupt:  # Return immediately with whatever is ready
                return default_path, body_sample_path
            except BaseException as e:
                print(f'{name} failed')
                traceback.print_exc()
                print(e)
                continue
        else: # On random body shape
            try:

                try:
                    fname1 = in_datapath / name / f'{name}_body_measurements.yaml'
                    fname2 = in_datapath / name / 'body_measurements.yaml'
                    fname = fname1 if fname1.exists() else fname2
                    rand_body = BodyParameters(fname)
                except FileNotFoundError:
                    if verbose:
                        print('FileNotFoundError::', fname)
                    continue   # Just skip examples without body files
                
                piece_shaped = MetaGarment(name, rand_body, design) 
                pattern = _save_sample(piece_shaped, rand_body, design, body_sample_data, verbose=verbose)
            except KeyboardInterrupt:  # Return immediately with whatever is ready
                return default_path, body_sample_path
            except BaseException as e:
                print(f'{name} failed')
                traceback.print_exc()
                print(e)
                
                continue
        
        # Update props and log every time
        if default_body:
            stats_utils.count_panels(pattern, new_props)
            stats_utils.garment_type(name, design, new_props)
            new_props.serialize(data_folder / 'dataset_properties.yaml')

    # log properties
    if default_body:
        new_props.stats_summary()
        new_props.serialize(data_folder / 'dataset_properties.yaml')

    return default_path, body_sample_path


def gather_visuals(path, verbose=False):
    vis_path = Path(path) / 'patterns_vis'
    vis_path.mkdir(parents=True, exist_ok=True)

    for p in path.rglob("*.png"):
        try: 
            shutil.copy(p, vis_path)
        except shutil.SameFileError:
            if verbose:
                print('File {} already exists'.format(p.name))
            pass


if __name__ == '__main__':
    system_props = Properties('./system.json')

    args = get_command_args()

    datasets = args.data
    body_types = [
        'default_body',
        'random_body'
    ]

    # (simulated) dataset to use
    for in_dataset in datasets:
        for body_type in body_types:
            
            print(f'INFO::Re-creating {in_dataset} for {body_type}')

            in_datapath = Path(system_props['garmentcodedata_gen']) / in_dataset / body_type
            props = Properties(Path(system_props['datasets_sim']) / in_dataset / body_type / f'dataset_properties_{body_type}.yaml', clean_stats=False)

            # Check packing
            # Check packing
            tars = list(in_datapath.glob('*.tar.gz'))
            for tar_path in tars:
                # NOTE: Unpacks and overwrites the dataset_properties files
                shutil.unpack_archive(tar_path, in_datapath)
                # Finally -- clean up
                tar_path.unlink()

            # Generator
            default_path, body_sample_path = generate(
                system_props['datasets_path'], props, in_datapath / 'data', system_props,
                default_body=(body_type == 'default_body'),
                # fail_types=[
                #     'stitching_error', 
                #     'pattern_loading', 
                #     'gt_edges_creation', 
                #     'meshgen-timeout', 
                #     # 'cloth_self_intersection',
                # ],
                verbose=False)

            # Gather the pattern images separately
            # NOTE: No need for images on the full data
            # if body_type == 'default_body':
            #     gather_visuals(default_path)
            # else:
            #     gather_visuals(body_sample_path)

            print('Data generation completed!')
