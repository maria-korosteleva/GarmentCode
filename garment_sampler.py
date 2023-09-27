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

# TODO Logging formatting

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

def _id_generator(size=10,
                  chars=string.ascii_uppercase + string.digits):
        """Generate a random string of a given size, see
        https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
        """
        return ''.join(random.choices(chars, k=size))

def generate(path, props, verbose=False):
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
    samples_folder = data_folder / 'data'

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
        # Redo sampling untill success
        for _ in range(100):  # Putting a limit on re-tries to avoid infinite loops
            new_design = sampler.randomize()
            name = f'rand_{_id_generator()}'
            try:
                # DEBUG
                if verbose:
                    print(f'{name} saving design params for debug')
                with open(Path('./Logs') / f'{name}_design_params.yaml', 'w') as f:
                    yaml.dump(
                        {'design': new_design}, 
                        f,
                        default_flow_style=False,
                        sort_keys=False
                    )

                piece = MetaGarment(name, body, new_design) 
                pattern = piece()

                if piece.is_self_intersecting():
                    if verbose:
                        print(f'{piece.name} is self-intersecting!!') 
                    continue  # Redo the randomization

                # Save as json file
                folder = pattern.serialize(
                    samples_folder, 
                    tag=datetime.now().strftime("%y%m%d-%H-%M-%S"),
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
                break  # Stop generation
            except BaseException as e:
                print(f'{name} failed')
                traceback.print_exc()
                print(e)
                
                # TODO Examine the errors -- probably there is something there
                continue

    elapsed = time.time() - start_time
    gen_stats['generation_time'] = f'{elapsed:.3f} s'

    # log properties
    props.serialize(data_folder / 'dataset_properties.yaml') 

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

    new = True
    if new:
        props = Properties()
        props.set_basic(
            design_file='./assets/design_params/default.yaml',
            body_file='./assets/body_measurments/f_smpl_avg.yaml',
            name='data_30',
            size=30,
            to_subfolders=True)
        props.set_section_config('generator')
    else:
        props = Properties(
            Path(system_props['datasets_path']) / 'data_30_230802-12-25-09/dataset_properties.yaml', 
            True)

    # Generator
    generate(system_props['datasets_path'], props, verbose=False)

    # Gather the pattern images separately
    gather_visuals(Path(system_props['datasets_path']) / props['data_folder'])

    # At the end -- it takes some time to gather the info
    # DRAFT props.add_sys_info()  # update this info regardless of the basic config    

    print('Data generation completed!')