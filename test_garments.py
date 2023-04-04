
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

if __name__ == '__main__':

    body_file = './assets/body_measurments/f_smpl_avg.yaml'
    # body_file = './assets/body_measurments/f_smpl_model.yaml'
    # body_file = './assets/body_measurments/f_smpl_model_fluffy.yaml'
    # body_file = './assets/body_measurments/m_smpl_avg.yaml'
    # body_file = './assets/body_measurments/sofia.yaml'  
    # body_file = './assets/body_measurments/ikea_toy.yaml'
    with open(body_file, 'r') as f:
        body = yaml.safe_load(f)['body']
        body['waist_level'] = body['height'] - body['head_l'] - body['waist_line']

    design_files = {
        'base': './assets/design_params/base.yaml',
        # 'Dress_20s': './assets/design_params/dress_20s.yaml',
        # 'Dress_30s': './assets/design_params/dress_30s.yaml',
        # 'Dress_40s': './assets/design_params/dress_40s.yaml',
        # 'Dress_50s': './assets/design_params/dress_50s.yaml',
        # 'Dress_regency': './assets/design_params/dress_regency.yaml',
        # 'sweatshirt': './assets/design_params/sweatshirt.yaml',
        # # 'pants': './assets/design_params/pants.yaml',
        # 'jumpsuit': './assets/design_params/jumpsuit.yaml',
    }
    designs = {}
    for df in design_files:
        with open(design_files[df], 'r') as f:
            designs[df] = yaml.safe_load(f)['design']
    
    test_garments = [
        # WB(),
        # CuffBand('test', design['pants']),
        # CuffSkirt('test', design['pants']),
        # CuffBandSkirt('test', design['pants'])
    ]
    for df in designs:
        test_garments.append(MetaGarment(df, body, designs[df]),)

    for piece in test_garments:
        pattern = piece()

        # Save as json file
        sys_props = Properties('./system.json')
        folder = pattern.serialize(
            Path(sys_props['output']), 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=False, 
            with_3d=True, with_text=True)

        shutil.copy(body_file, folder)
        if piece.name in design_files:
            shutil.copy(design_files[piece.name], folder)
        else:
            shutil.copy(design_files['base'], folder)

        print(f'Success! {piece.name} saved to {folder}')