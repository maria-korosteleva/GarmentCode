"""
    Fitting one sewing pattern design to a set of various body shapes
"""

from datetime import datetime
from pathlib import Path
import yaml
import shutil 
import time
import traceback
import argparse

# Custom
from pygarment.data_config import Properties
from assets.garment_programs.meta_garment import MetaGarment
from assets.bodies.body_params import BodyParameters

def get_command_args():
    """command line arguments to control the run"""
    # https://stackoverflow.com/questions/40001892/reading-named-command-arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('design_file', help='Path to design parameters file to be used to fit to the bodies', type=str)
    parser.add_argument('--batch_id', '-b', help='id of a sampling batch', type=int, default=None) 
    parser.add_argument('--size', '-s', help='size of a sample', type=int, default=10)
    parser.add_argument('--name', '-n', help='Name of the dataset', type=str, default='design_fit')
    parser.add_argument('--replicate', '-re', help='Name of the dataset to re-generate. If set, other arguments are ignored', type=str, default=None)
    

    args = parser.parse_args()
    print('Commandline arguments: ', args)

    return args

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

    bodies = []
    for file in objs_path.iterdir():
        
        # Get name
        b_name = file.stem.split('_')[0]
        bodies.append({})

        # Get obj options
        bodies[-1]['objs'] = dict(
            straight=f'meshes/{b_name}_straight.obj', 
            apart=f'meshes/{b_name}_apart.obj', )

        # Get measurements
        bodies[-1]['mes'] = f'measurements/{b_name}.yaml'
    
    return bodies


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

    # generate data
    start_time = time.time()

    # Load design 
    with open(properties['design_file'], 'r') as f:
        design = yaml.safe_load(f)['design']

    # On default body
    default_body = BodyParameters(Path(sys_paths['bodies_default_path']) / (properties['body_default'] + '.yaml'))
    piece_default = MetaGarment(properties['body_default'], default_body, design) 
    _save_sample(piece_default, default_body, design, default_sample_data, verbose=verbose)
                
    
    for i in range(properties['size']):
        # log properties every time
        properties.serialize(data_folder / 'dataset_properties.yaml')

        try:
            # On random body shape
            rand_body = body_sample(
                i + properties['body_sample_start_id'],
                body_options,
                body_samples_path,
                straight='Pants' != design['meta']['bottom']['v'])
            name = rand_body.params['body_sample']

            piece_shaped = MetaGarment(name, rand_body, design) 
            
            # Save samples
            _save_sample(piece_shaped, rand_body, design, body_sample_data, verbose=verbose)
        except KeyboardInterrupt:  # Return immediately with whatever is ready
            return default_path, body_sample_path
        except BaseException as e:
            print(f'{name} failed')
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

    args = get_command_args()

    if args.replicate is not None:
        props = Properties(
            Path(system_props['datasets_path']) / args.replicate / 'dataset_properties.yaml',
            True)
    else:
        props = Properties()
        props.set_basic(
            design_file=args.design_file,
            body_default='mean_all',
            body_samples='5000_body_shapes_and_measures',
            body_sample_start_id=0,
            name=f'{args.name}_{args.size}' if not args.batch_id else f'{args.name}_{args.size}_{args.batch_id}',
            size=args.size,
            to_subfolders=True)
        props.set_section_config('generator')

    # Generator
    default_path, body_sample_path = generate(
        system_props['datasets_path'], props, system_props, verbose=False)

    # Gather the pattern images separately
    gather_visuals(default_path)
    gather_visuals(body_sample_path)

    # At the end -- it takes some time to gather the info
    props.add_sys_info()  

    print('Data generation completed!')
