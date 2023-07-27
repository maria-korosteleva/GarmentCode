
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

    # TODO Correct dataset structure

    new_design = sampler.randomize()
    piece = MetaGarment('Random', body, new_design)

    pattern = piece()

    # TODO Quality checks

    # Save as json file
    sys_props = Properties('./system.json')
    folder = pattern.serialize(
        Path(sys_props['output']), 
        tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
        to_subfolder=False, 
        with_3d=True, with_text=False, view_ids=False)

    body.save(folder)
    # TODO Save current design as well

    print(f'Success! {piece.name} saved to {folder}')