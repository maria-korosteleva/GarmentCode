"""
    Package for to simulate garments from patterns in Maya with Qualoth. 

    Main dependencies:
        * Maya 2022+ (uses Python 3.6+)
        * Arnold Renderer
        * Qualoth (compatible with your Maya version)
    
    To run the package in Maya don't foget to add it to PYTHONPATH!
"""
from importlib import reload

import mayaqltools.mayascene as mayascene
reload(mayascene)

from .mayascene import PatternLoadingError, MayaGarment, Scene, MayaGarmentWithUI

import mayaqltools.simulation as simulation
import mayaqltools.qualothwrapper as qualothwrapper
import mayaqltools.garmentUI as garmentUI
import mayaqltools.scan_imitation as scan_imitation
import mayaqltools.utils as utils

reload(simulation)
reload(qualothwrapper)
reload(garmentUI)
reload(scan_imitation)
reload(utils)
