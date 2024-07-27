"""In simulated dataset, gather all the scene images in one folder"""

import meshgen.external.customconfig as customconfig
from pathlib import Path
import shutil

from datasim import gather_renders


system_props = customconfig.Properties('./system.json')
dataset = 'unpacking_test'
datapaths = [
    Path(system_props['output']) / dataset / 'default_body', 
    Path(system_props['output']) / dataset / 'random_body'
]

for datapath in datapaths:
    # Check packing
    tar_path = datapath / 'data.tar.gz'
    if tar_path.exists():
        shutil.unpack_archive(tar_path, datapath)
        # Finally -- clean up
        tar_path.unlink()

    gather_renders(datapath)
