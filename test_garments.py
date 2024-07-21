from datetime import datetime
import shutil
from pathlib import Path
import yaml
import sys
import os
sys.path.append(str((Path(os.getcwd()) / 'external').resolve()))

from assets.garment_programs.meta_garment import MetaGarment
from assets.bodies.body_params import BodyParameters
from external.customconfig import Properties

if __name__ == '__main__':

    # 
    # body_file = './assets/body_measurments/f_smpl_avg.yaml'
    body_file = './assets/default_bodies/mean_all.yaml'
    # body_file = 

    body = BodyParameters(body_file)

    design_files = {
        'base': './assets/design_params/base.yaml',
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
        test_garments.append(MetaGarment(df, body, designs[df]))
        try:
            test_garments[-1].assert_total_length()
        except BaseException as e:
            print(e)
            pass

    for piece in test_garments:
        pattern = piece.assembly()

        if piece.is_self_intersecting():
            print(f'{piece.name} is Self-intersecting')

        # Save as json file
        sys_props = Properties('./system.json')
        folder = pattern.serialize(
            # Path(r"G:\My Drive\GarmentCode\sewing_siggraph_garment\Fits"),  #   
            Path(sys_props['output']), 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=False, 
            with_3d=False, with_text=False, view_ids=False)

        body.save(folder)
        if piece.name in design_files:
            shutil.copy(design_files[piece.name], folder)
        else:
            shutil.copy(design_files['base'], folder)

        print(f'Success! {piece.name} saved to {folder}')
