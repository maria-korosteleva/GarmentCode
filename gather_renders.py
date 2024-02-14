"""In simulated dataset, gather all the scene images in one folder"""

import customconfig
from pathlib import Path

from garment_sampler import gather_visuals


system_props = customconfig.Properties('./system.json')
dataset = 'test_drag_fixes_100_240209-16-27-32'
def_datapath = Path(system_props['datasets_path']) / dataset / 'default_body'
rand_datapath = Path(system_props['datasets_path']) / dataset / 'random_body'

gather_visuals(def_datapath)
gather_visuals(rand_datapath)
