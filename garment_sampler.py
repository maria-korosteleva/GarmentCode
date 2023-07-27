"""A modified version of the data generation file from here: 
https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/data_generation/datagenerator.py
"""

from datetime import datetime
from pathlib import Path
import yaml
import sys
import shutil 

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
from assets.garment_programs.random_tests import *   # DEBUG

from assets.body_measurments.body_params import BodyParameters

import pypattern as pyp

def _create_data_folder(folder_name, path='', props=''):
    """ Create a new directory to put dataset in 
        & generate appropriate name & update dataset properties
    """
    # DRAFT if 'data_folder' in props:  # will this work?
    #     # => regenerating from existing data
    #     props['name'] = props['data_folder'] + '_regen'
    #     data_folder = props['name']
    # else:
    #     data_folder = props['name'] + '_' + Path(props['templates']).stem

    # make unique
    data_folder = folder_name
    data_folder += '_' + datetime.now().strftime('%y%m%d-%H-%M-%S')
    # DRAFT props['data_folder'] = data_folder
    path_with_dataset = Path(path) / data_folder
    path_with_dataset.mkdir(parents=True)

    return path_with_dataset

if __name__ == '__main__':

    # TODO Body sampling as well?
    body_file = './assets/body_measurments/f_smpl_avg.yaml'
    # body_file = './assets/body_measurments/f_avatar.yaml'
    # body_file = './assets/body_measurments/f_smpl_model.yaml'
    # body_file = './assets/body_measurments/f_smpl_model_fluffy.yaml'
    # body_file = './assets/body_measurments/m_smpl_avg.yaml'

    body = BodyParameters(body_file)

    design_file = './assets/design_params/default.yaml'
    sampler = pyp.params.DesignSampler(design_file)
    sys_props = Properties('./system.json')

    data_folder = _create_data_folder('data_sampling', sys_props['datasets_path'])

    # TODO dataset properties file!
    for i in range(5):
        new_design = sampler.randomize()
        piece = MetaGarment(f'Random_{i}', body, new_design)
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