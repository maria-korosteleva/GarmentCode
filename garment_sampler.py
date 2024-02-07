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
from external.customconfig import Properties
from assets.garment_programs.skirt_paneled import *
from assets.garment_programs.tee import *
from assets.garment_programs.godet import *
from assets.garment_programs.bodice import *
from assets.garment_programs.pants import *
from assets.garment_programs.meta_garment import *
from assets.garment_programs.bands import *
from assets.body_measurments.body_params import BodyParameters
import pypattern as pyp

def _create_data_folder(properties, path=Path('')):
    """ Create a new directory to put dataset in 
        & generate appropriate name & update dataset properties
    """
    if 'data_folder' in properties:  # will this work?
        # => regenerating from existing data
        properties['name'] = properties['data_folder'] + '_regen'
        data_folder = properties['name']
    else:
        data_folder = properties['name']

    # make unique
    data_folder += '_' + datetime.now().strftime('%y%m%d-%H-%M-%S')
    properties['data_folder'] = data_folder
    path_with_dataset = path / data_folder
    path_with_dataset.mkdir(parents=True)

    default_folder = path_with_dataset / 'default_body'
    body_folder = path_with_dataset / 'random_body'

    default_folder.mkdir(parents=True, exist_ok=True)
    body_folder.mkdir(parents=True, exist_ok=True)

    return path_with_dataset, default_folder, body_folder

def _gather_body_options(body_path: Path):
    objs_path = body_path / 'measurements'

    bodies = {}
    for file in objs_path.iterdir():
        
        # Get name
        b_name = file.stem.split('_')[0]
        bodies[b_name] = {}

        # TODO With or withough subpath? -- check integration with sim loading
        # Get obj options
        bodies[b_name]['objs'] = dict(
            straight=f'meshes/{b_name}_straight.obj', 
            apart=f'meshes/{b_name}_apart.obj', )

        # Get measurements
        bodies[b_name]['mes'] = f'measurements/{b_name}.yaml'
    
    return bodies


def _id_generator(size=10, chars=string.ascii_uppercase + string.digits):
        """Generate a random string of a given size, see
        https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
        """
        return ''.join(random.choices(chars, k=size))

def body_sample(bodies: dict, path: Path, straight=True):

    rand_name = random.sample(list(bodies.keys()), k=1)
    body_i = bodies[rand_name[0]]

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
        with_3d=False, with_text=False, view_ids=False)

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

def has_pants(design):
    return 'Pants' == design['meta']['bottom']['v']


def generate(path, properties, sys_paths, verbose=False):
    """Generates a synthetic dataset of patterns with given properties
        Params:
            path : path to folder to put a new dataset into
            props : an instance of DatasetProperties class
                    requested properties of the dataset
    """
    path = Path(path)
    gen_config = properties['generator']['config']
    gen_stats = properties['generator']['stats']
    body_samples_path = Path(sys_paths['body_samples_path']) / properties['body_samples']
    body_options = _gather_body_options(body_samples_path)

    # create data folder
    data_folder, default_path, body_sample_path = _create_data_folder(properties, path)
    default_sample_data = default_path / 'data'
    body_sample_data = body_sample_path / 'data'

    # init random seed
    if 'random_seed' not in gen_config or gen_config['random_seed'] is None:
        gen_config['random_seed'] = int(time.time())
    print(f'Random seed is {gen_config["random_seed"]}')
    random.seed(gen_config['random_seed'])

    # generate data
    start_time = time.time()

    default_body = BodyParameters(Path(sys_paths['bodies_default_path']) / (properties['body_default'] + '.yaml'))
    sampler = pyp.params.DesignSampler(properties['design_file'])
    for i in range(properties['size']):
        # log properties every time
        properties.serialize(data_folder / 'dataset_properties.yaml')

        # Redo sampling untill success
        for _ in range(100):  # Putting a limit on re-tries to avoid infinite loops
            new_design = sampler.randomize()
            name = f'rand_{_id_generator()}'
            try:
                if verbose:
                    print(f'{name} saving design params for debug')
                    with open(Path('./Logs') / f'{name}_design_params.yaml', 'w') as f:
                        yaml.dump(
                            {'design': new_design}, 
                            f,
                            default_flow_style=False,
                            sort_keys=False
                        )

                # On default body
                piece_default = MetaGarment(name, default_body, new_design) 
                # Check quality
                piece_default.assert_total_length() 
                piece_default.assert_non_empty(filter_belts=True)  # Enough to check for default

                # Straight/apart legs pose
                def_obj_name = properties['body_default']
                if has_pants(new_design):
                    def_obj_name += '_apart'
                default_body.params['body_sample'] = def_obj_name

                # On random body shape
                rand_body = body_sample(
                    body_options,
                    body_samples_path,
                    straight=not has_pants(new_design))
                piece_shaped = MetaGarment(name, rand_body, new_design) 
                piece_shaped.assert_total_length()   # Check final length correctness
                
                if piece_default.is_self_intersecting() or piece_shaped.is_self_intersecting():
                    if verbose:
                        print(f'{piece_default.name} is self-intersecting!!') 
                    continue  # Redo the randomization
                
                # Save samples
                _save_sample(piece_default, default_body, new_design, default_sample_data, verbose=verbose)
                _save_sample(piece_shaped, rand_body, new_design, body_sample_data, verbose=verbose)
                
                break  # Stop generation
            except KeyboardInterrupt:  # Return immediately with whatever is ready
                return default_path, body_sample_path
            except BaseException as e:
                print(f'{name} failed')
                if verbose:
                    traceback.print_exc()
                print(e)
                
                continue

    elapsed = time.time() - start_time
    gen_stats['generation_time'] = f'{elapsed:.3f} s'

    # log properties
    properties.serialize(data_folder / 'dataset_properties.yaml')

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

    new = True
    if new:
        props = Properties()
        props.set_basic(
            design_file='./assets/design_params/default.yaml',
            body_default='mean_all',
            body_samples='garment-first-samples',
            name='data_100',
            size=100,
            to_subfolders=True)
        props.set_section_config('generator')
    else:
        props = Properties(
            Path(system_props['datasets_path']) / 'data_30_231116-17-26-02/dataset_properties.yaml',
            True)

    # Generator
    default_path, body_sample_path = generate(
        system_props['datasets_path'], props, system_props, verbose=False)

    # Gather the pattern images separately
    gather_visuals(default_path)
    gather_visuals(body_sample_path)

    # At the end -- it takes some time to gather the info
    # DRAFT props.add_sys_info()  # update this info regardless of the basic config    

    print('Data generation completed!')
