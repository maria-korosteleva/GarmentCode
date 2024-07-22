"""In simulated dataset, gather all the scene images in one folder"""

from pygarment import customconfig
from pathlib import Path
import shutil

from garment_sampler import gather_visuals


system_props = customconfig.Properties('./system.json')
dataset = 'test_unpacking'

datapaths = [
    Path(system_props['datasets_path']) / dataset / 'default_body', 
    Path(system_props['datasets_path']) / dataset / 'random_body'
]

for datapath in datapaths:
    # Check packing
    tar_path = datapath / 'data.tar.gz'
    if tar_path.exists():
        shutil.unpack_archive(tar_path, datapath)
        # Finally -- clean up
        tar_path.unlink()

    gather_visuals(datapath)