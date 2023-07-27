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

sys.path.insert(0, './external/')
sys.path.insert(1, './')

# Custom
from customconfig import Properties
from assets.garment_programs.skirt_paneled import *
from assets.garment_programs.tee import *
from assets.garment_programs.godet import *
from assets.garment_programs.bodice import *
from assets.garment_programs.pants import *
from assets.garment_programs.meta_garment import *
from assets.garment_programs.bands import *

from assets.body_measurments.body_params import BodyParameters

import pypattern as pyp

def _create_data_folder(path='', props=''):
    """ Create a new directory to put dataset in 
        & generate appropriate name & update dataset properties
    """
    if 'data_folder' in props:  # will this work?
        # => regenerating from existing data
        props['name'] = props['data_folder'] + '_regen'
        data_folder = props['name']
    else:
        data_folder = props['name']

    # make unique
    data_folder += '_' + datetime.now().strftime('%y%m%d-%H-%M-%S')
    props['data_folder'] = data_folder
    path_with_dataset = Path(path) / data_folder
    path_with_dataset.mkdir(parents=True)

    return path_with_dataset

def generate(path, props):
    """Generates a synthetic dataset of patterns with given properties
        Params:
            path : path to folder to put a new dataset into
            props : an instance of DatasetProperties class
                    requested properties of the dataset
    """
    path = Path(path)
    gen_config = props['generator']['config']
    gen_stats = props['generator']['stats']

    # create data folder
    data_folder = _create_data_folder(path, props)

    # init random seed
    if 'random_seed' not in gen_config or gen_config['random_seed'] is None:
        gen_config['random_seed'] = int(time.time())
    random.seed(gen_config['random_seed'])

    # generate data
    start_time = time.time()

    # TODO Body sampling as well?
    body = BodyParameters(props['body_file'])
    sampler = pyp.params.DesignSampler(props['design_file'])
    for i in range(props['size']):
        new_design = sampler.randomize()

        try:
            piece = MetaGarment(f'Random_{i}', body, new_design)  # TODO Naming
            pattern = piece()

            # TODO Quality checks (!!!) -- probably best if they are internal to the sampler?
            # Or how will I do that?
            # Save as json file
            folder = pattern.serialize(
                data_folder, 
                tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
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
            print(f'Success! {piece.name} saved to {folder}')
        except BaseException as e:
            print(f'{i} failed')
            print(e)
            # TODO redo sampling untill success
            # TODO Examine the errors
            continue

    elapsed = time.time() - start_time
    gen_stats['generation_time'] = f'{elapsed:.3f} s'

    # log properties
    props.serialize(data_folder / 'dataset_properties.yaml')  # TODO Support YAML

if __name__ == '__main__':

    system_props = Properties('./system.json')

    new = True
    if new:
        props = Properties()
        props.set_basic(
            design_file='./assets/design_params/default.yaml',
            body_file='./assets/body_measurments/f_smpl_avg.yaml',
            name='data_5',
            size=5,
            to_subfolders=True)
        props.set_section_config('generator')
    else:
        props = Properties(
            Path(system_props['datasets_path']) / 'data_5_230727-17-30-03/dataset_properties.json', 
            True)

    # Generator
    generate(system_props['datasets_path'], props)

    # TODO Gather the pattern images separately

    # At the end -- it takes some time to gather the info
    props.add_sys_info()  # update this info regardless of the basic config    

    print('Data generation completed!')