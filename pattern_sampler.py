"""
    Create a random sample of sewing pattern designs and fit each
    to a neutral and a random body shape 
"""

from datetime import datetime
from pathlib import Path
import yaml
import shutil 
import time
import random
import string
import traceback
import argparse

# Custom
from pygarment.data_config import Properties
from assets.garment_programs.meta_garment import MetaGarment, IncorrectElementConfiguration
from assets.bodies.body_params import BodyParameters
import pygarment as pyg
import assets.garment_programs.stats_utils as stats_utils

def get_command_args():
    """command line arguments to control the run"""
    # https://stackoverflow.com/questions/40001892/reading-named-command-arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch_id', '-b', help='id of a sampling batch', type=int, default=None)
    parser.add_argument('--size', '-s', help='size of a sample', type=int, default=10)
    parser.add_argument('--name', '-n', help='Name of the dataset', type=str, default='data')
    parser.add_argument('--replicate', '-re', help='Name of the dataset to re-generate. If set, other arguments are ignored', type=str, default=None)
    
    args = parser.parse_args()
    print('Commandline arguments: ', args)

    return args

# Utils
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

def gather_body_options(body_path: Path):
    objs_path = body_path / 'measurements'

    bodies = {}
    for file in objs_path.iterdir():
        
        # Get name
        b_name = file.stem.split('_')[0]
        bodies[b_name] = {}

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

    return pattern

def has_pants(design):
    return 'Pants' == design['meta']['bottom']['v']

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

# Quality filter
def assert_param_combinations(design, filter_belts=True):
    """Check for some known invalid parameter combinations cases"""
    upper_name = design['meta']['upper']['v']
    lower_name = design['meta']['bottom']['v']
    belt_name = design['meta']['wb']['v']

    if upper_name:  # No issues with garments that can hang on shoulders
        return

    # Empty patterns and singular belts
    if not lower_name:
        if filter_belts or not belt_name:
            raise IncorrectElementConfiguration('ERROR::IncorrectParams::Empty pattern or singular belt')
        return
    
    # Cases when lower name is present (and maybe a belt):
    # All pants and pencils are okay
    if lower_name in ['Pants', 'PencilSkirt']:
        return

    # -- Sliding issues --
    # NOTE: Checks are conservative, so some sliding issues might be present nontheless 
    # Skirt 2 & skirts of top of it -- uses ruffles and belt is too wide if even present
    if (lower_name == 'Skirt2'
            or lower_name == 'GodetSkirt' and design['godet-skirt']['base']['v'] == 'Skirt2'
            or lower_name == 'SkirtLevels' and design['levels-skirt']['base']['v'] == 'Skirt2'
        ):

        if (design['skirt']['ruffle']['v'] > 1 and (not belt_name or design['waistband']['waist']['v'] > 1.)):
            raise IncorrectElementConfiguration('ERROR::IncorrectParams::Skirt2 ruffles + belt')

    # Flare skirts & skirts on top of it -- no belt + too wide / too long
    flare_skirts = ['SkirtCircle', 'AsymmSkirtCircle', 'SkirtManyPanels']
    if (lower_name in flare_skirts
            or lower_name == 'SkirtLevels' and design['levels-skirt']['base']['v'] in flare_skirts
        ):
        # if Fitted belt of enough width not present -- check if "heavy"
        if (not belt_name 
                or design['waistband']['waist']['v'] > 1.
                or design['waistband']['width']['v'] <= 0.25
            ):
            length_param = design['levels-skirt' if lower_name == 'SkirtLevels' else 'flare-skirt']['length']['v'] 
            if length_param > 0.5 or design['flare-skirt']['suns']['v'] > 0.75:
                raise IncorrectElementConfiguration('ERROR::IncorrectParams::Flare skirts + belt')


# Generation loop
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
    body_options = gather_body_options(body_samples_path)

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
    sampler = pyg.DesignSampler(properties['design_file'])
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

                # Preliminary checks 
                assert_param_combinations(new_design)

                # On default body
                piece_default = MetaGarment(name, default_body, new_design) 
                piece_default.assert_total_length()  # Check final length correctnesss

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
                pattern = _save_sample(piece_default, default_body, new_design, default_sample_data, verbose=verbose)
                _save_sample(piece_shaped, rand_body, new_design, body_sample_data, verbose=verbose)
                
                stats_utils.count_panels(pattern, props)
                stats_utils.garment_type(name, new_design, props)

                break  # Stop generation
            except KeyboardInterrupt:  # Return immediately with whatever is ready
                return default_path, body_sample_path
            except BaseException as e:
                print(f'{name} failed')
                if verbose:
                    traceback.print_exc()
                print(e)

                # Check empty folder
                if (default_sample_data / name).exists():
                    print('Generate::Info::Removed empty folder after unsuccessful sampling attempt', default_sample_data / name)
                    shutil.rmtree(default_sample_data / name, ignore_errors=True)
                
                if (body_sample_data / name).exists():
                    print('Generate::Info::Removed empty folder after unsuccessful sampling attempt', body_sample_data / name)
                    shutil.rmtree(body_sample_data / name, ignore_errors=True)

                continue

    elapsed = time.time() - start_time
    gen_stats['generation_time'] = f'{elapsed:.3f} s'

    # log properties
    props.stats_summary()
    properties.serialize(data_folder / 'dataset_properties.yaml')

    return default_path, body_sample_path



if __name__ == '__main__':

    system_props = Properties('./system.json')

    args = get_command_args()

    if args.replicate is not None:
        props = Properties(
            Path(system_props['datasets_path']) / args.replicate / 'dataset_properties.yaml',
            True)
    else:  # New sample
        props = Properties()
        props.set_basic(
            design_file='./assets/design_params/default.yaml',
            body_default='mean_all',
            body_samples='5000_body_shapes_and_measures', 
            size=args.size,
            name=f'{args.name}_{args.size}' if not args.batch_id else f'{args.name}_{args.size}_{args.batch_id}',
            to_subfolders=True)
        props.set_section_config('generator')
        props.set_section_stats(
            'generator', 
            panel_count={},
            garment_types={},
            garment_types_summary=dict(main={}, style={})
        )
        

    # Generator
    default_path, body_sample_path = generate(
        system_props['datasets_path'], props, system_props, verbose=False)

    # Gather the pattern images separately
    gather_visuals(default_path)
    gather_visuals(body_sample_path)

    print('Data generation completed!')
