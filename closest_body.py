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

def mes_distance(mes_1, mes_2):

    # TODO Weights on more important values? 
    diffs = []
    for key, value in mes_1.items():
        value_2 = mes_2[key]

        diffs.append((value - value_2)**2)

    return np.mean(diffs)

def find_closest_body(body_folder_path, body_options, in_mes_path):

    with open(in_mes_path, 'r') as f:
        in_mes = yaml.load(f, Loader=yaml.SafeLoader)['body']


    dists = []
    bodies_list = list(body_options.keys())
    for body in bodies_list:
        with open(body_folder_path / body_options[body]['mes'], 'r') as f:
            body_mes = yaml.load(f, Loader=yaml.SafeLoader)['body']

        dists.append(mes_distance(in_mes, body_mes))

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

    
# TODO pre-load bodies for acceleration 

if __name__ == '__main__':

    system_props = Properties('./system.json')

    body_samples_folder = '2023_12_30_shapes_and_measures'  #  'garment-first-samples'

    # TODO As argument
    # DRAFT in_body_mes = r"G:\My Drive\GarmentCode\sewing_siggraph_garment\measurements\Maria_updated.yaml"
    # in_body_mes = r"C:\Users\MariaKo\Documents\Code\Procedural-Garments\assets\default_bodies\mean_female.yaml"
    in_body_mes = r"C:\Users\MariaKo\Documents\Code\Procedural-Garments\assets\default_bodies\mean_male.yaml"

    body_samples_path = Path(system_props['body_samples_path']) / body_samples_folder
    body_options = gather_body_options(body_samples_path)

    closest_body = find_closest_body(body_samples_path, body_options, in_body_mes)

    print('Found closest body!:', closest_body)

