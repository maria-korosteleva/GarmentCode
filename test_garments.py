
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

    body_file = './assets/GarmentCode/options_body.yaml'
    design_file = './assets/GarmentCode/options_design.yaml'
    with open(body_file, 'r') as f:
        body = yaml.safe_load(f)['body']
        body['waist_level'] = body['height'] - body['head_l'] - body['waist_line']
    with open(design_file, 'r') as f:
        design = yaml.safe_load(f)['design']
    test_garments = [
        # SkirtWB(1),
        # SkirtWB(1.5, 0),
        # SkirtWB(2, 0),
        # SkirtWB(2),
        # WB(),
        # Skirt2(),
        # SkirtManyPanels(body, n_panels=10),
        # SkirtManyPanelsWB(body, design),
        # Shirt(body, design),
        # FittedShirt(body, design),
        # GodetSkirt(body, design),
        # Pants(body, design),
        WBPants(body, design),
        # MetaGarment('Jumpsuit', body, design),
        # CuffBand('test', design['pants']),
        # CuffSkirt('test', design['pants']),
        # CuffBandSkirt('test', design['pants'])
    ]

    # test_garments[0].translate_by([2, 0, 0])

    for piece in test_garments:
        pattern = piece()

        # Save as json file
        sys_props = Properties('./system.json')
        folder = pattern.serialize(
            Path(sys_props['output']), 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=False)

        shutil.copy(body_file, folder)
        shutil.copy(design_file, folder)

        print(f'Success! {piece.name} saved to {folder}')