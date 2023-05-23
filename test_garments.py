
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

from assets.body_measurments.body_params import BodyParameters

if __name__ == '__main__':
    bodies_measurements = {
        'avg': './assets/body_measurments/f_smpl_avg.yaml',
        'thin': './assets/body_measurments/f_smpl_model.yaml',
        'fluffy': './assets/body_measurments/f_smpl_model_fluffy.yaml',
        'man': './assets/body_measurments/m_smpl_avg.yaml'
    }
    body_to_use = 'thin'   # CHANGE HERE to use different set of body measurements

    body = BodyParameters(bodies_measurements[body_to_use])

    design_files = {
        'default': './assets/design_params/default.yaml',    
        # Add paths HERE to load other parameters
    }
    designs = {}
    for df in design_files:
        with open(design_files[df], 'r') as f:
            designs[df] = yaml.safe_load(f)['design']
    
    test_garments = [MetaGarment(df, body, designs[df]) for df in designs]
    outpath = Path('./Logs')
    outpath.mkdir(parents=True, exist_ok=True)
    for piece in test_garments:
        pattern = piece()

        # Save as json file
        folder = pattern.serialize(
            outpath, 
            tag=datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=True, with_text=False, view_ids=False)

        body.save(folder)
        if piece.name in design_files:
            shutil.copy(design_files[piece.name], folder)
        else:
            shutil.copy(design_files['default'], folder)

        print(f'Success! {piece.name} saved to {folder}')
