"""Find the body among the available set of body shapes that is the closest to the input set of measurements"""
import numpy as np
from pathlib import Path
import sys
import yaml
sys.path.insert(0, './external/')
sys.path.insert(1, './')

# Custom
from external.customconfig import Properties
from garment_sampler import gather_body_options

def load_mesurements(body_folder_path, body_options):
    for body in body_options:
        with open(body_folder_path / body_options[body]['mes'], 'r') as f:
            body_options[body]['mes_list'] = yaml.load(f, Loader=yaml.SafeLoader)['body']


def mes_distance(mes_1, mes_2, important_only=False):
    # TODO Weights on more important values? 

    important = [
        'shoulder_w', 
        'arm_length', 
        'waist', 
        'waist_line',
        'waist_over_bust_line',
        'waist_back_width',
        'bust_line',
        'bust',
        'back_width',
        'hips',
        'hips_line',
        'hip_back_width'
    ]
    
    key_list = important if important_only else mes_1.keys()

    diffs = []
    for key in key_list:
        value = mes_1[key]
        value_2 = mes_2[key]

        diffs.append((value - value_2)**2)

    return np.mean(diffs)

def find_closest_body(body_options, in_mes_path, important_only=False):

    with open(in_mes_path, 'r') as f:
        in_mes = yaml.load(f, Loader=yaml.SafeLoader)['body']

    dists = []
    bodies_list = list(body_options.keys())
    # NOTE: parallelizable? 
    for body in bodies_list:
        body_mes = body_options[body]['mes_list']
        dists.append(mes_distance(in_mes, body_mes, important_only=important_only))

    min_id = np.argmin(dists)
    min_body = bodies_list[min_id]
    min_dist = dists[min_id]

    # For fun
    max_id = np.argmax(dists)
    max_body, max_dist = bodies_list[max_id], dists[max_id]

    # DEBUG
    print('Min distances! ', min_body, min_dist)
    print('Max distances! ', max_body, max_dist)

    return min_body

if __name__ == '__main__':

    system_props = Properties('./system.json')

    body_samples_folder = '2023_12_30_shapes_and_measures'  #  'garment-first-samples'

    # TODO As argument
    in_body_mes = [
        r"C:\Users\MariaKo\Documents\Code\Procedural-Garments\assets\bodies\mean_female.yaml",
        r"G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Maria_updated.yaml",
        r"G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Olga_updated.yaml",
        r"G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Jana_updated.yaml"
    ]
    # in_body_mes = r"C:\Users\MariaKo\Documents\Code\Procedural-Garments\assets\bodies\mean_male.yaml"

    body_samples_path = Path(system_props['body_samples_path']) / body_samples_folder
    body_options = gather_body_options(body_samples_path)
    load_mesurements(body_samples_path, body_options)

    for in_path in in_body_mes:
        closest_body = find_closest_body(body_options, in_path, important_only=True)

        # DEBUG
        print(in_path)
        print('Found closest body!:', closest_body)
        print('-------------------------------------')


# Maria
# Min distances!  01710 11.066555912899998
# Max distances!  04425 385.320189147204
# Found closest body!: 01710

# Olga
# Min distances!  03069 11.307246788919999
# Max distances!  04425 286.427791547204
# Found closest body!: 03069

# Jana
# Min distances!  04438 10.889674696560006
# Max distances!  04425 244.805458747204
# Found closest body!: 04438


# Min distances!  01242 7.005999928333334
# Max distances!  04425 565.9370337791668
# G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Maria_updated.yaml
# Found closest body!: 01242
# -------------------------------------
# Min distances!  00811 7.460240216666661
# Max distances!  04425 401.73797044583335
# G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Olga_updated.yaml
# Found closest body!: 00811
# -------------------------------------
# Min distances!  00864 3.676784292500001
# Max distances!  04425 334.0898204458334
# G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Jana_updated.yaml
# Found closest body!: 00864
# -------------------------------------