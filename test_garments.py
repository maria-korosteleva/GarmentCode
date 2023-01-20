
from datetime import datetime
from pathlib import Path
import yaml
import sys
import shutil 

# DRAFT site.addsitedir('../external/')
sys.path.insert(0, './external/')

# Custom
from customconfig import Properties
from assets.GarmentCode.skirt_paneled import *
from assets.GarmentCode.tee import *
from assets.GarmentCode.godet import *
from assets.GarmentCode.bodice import *
from assets.GarmentCode.pants import *
from assets.GarmentCode.meta_garment import *
from assets.GarmentCode.bands import *

if __name__ == '__main__':

    body_file = './assets/body_measurments/f_smpl_avg.yaml'
    body_file = './assets/body_measurments/f_smpl_model.yaml'
    with open(body_file, 'r') as f:
        body = yaml.safe_load(f)['body']
        body['waist_level'] = body['height'] - body['head_l'] - body['waist_line']

    design_files = {
        # 'base': './assets/GarmentCode/options_design.yaml',
        # 'Dress_20s': './assets/design_params/dress_20s.yaml',
        # 'Dress_30s': './assets/design_params/dress_30s.yaml',
        'Dress_50s': './assets/design_params/dress_50s.yaml',
        # 'Dress_regency': './assets/design_params/dress_regency.yaml'
    }
    designs = {}
    for df in design_files:
        with open(design_files[df], 'r') as f:
            designs[df] = yaml.safe_load(f)['design']
    
    test_garments = [
        # SkirtWB(body, design),
        # WB(),
        # Skirt2(),
        # SkirtManyPanels(body, n_panels=10),
        # SkirtManyPanelsWB(body, design),
        # Shirt(body, design),
        # FittedShirt(body, design),
        # GodetSkirt(body, designs['base']),
        # Pants(body, design),
        # WBPants(body, design),
        # CuffBand('test', design['pants']),
        # CuffSkirt('test', design['pants']),
        # CuffBandSkirt('test', design['pants'])
        # PencilSkirt(body, design)
    ]
    for df in designs:
        test_garments.append(MetaGarment(df, body, designs[df]),)

    # test_garments[0].translate_by([2, 0, 0])

    for piece in test_garments:
        pattern = piece()

        # Save as json file
        sys_props = Properties('./system.json')
        folder = pattern.serialize(
            Path(sys_props['output']), 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=False, 
            with_3d=False, with_text=False)

        shutil.copy(body_file, folder)
        if piece.name in design_files:
            shutil.copy(design_files[piece.name], folder)
        else:
            shutil.copy(design_files['base'], folder)

        print(f'Success! {piece.name} saved to {folder}')