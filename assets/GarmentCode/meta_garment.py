
""" A Meta garment component!
    Depending on parameter values it can generate sewing patterns 
    for various dresses and jumpsuit styles and fit them to the body measurements
"""

# Custom
import pypattern as pyp

from assets.GarmentCode.skirt_paneled import *
from assets.GarmentCode.tee import *
from assets.GarmentCode.godet import *
from assets.GarmentCode.bodice import *
from assets.GarmentCode.pants import *
from assets.GarmentCode.bands import *


# TODO Check that all component follow the same interface conventions
# And this works for all
# TODO Panel name uniqueness
class MetaGarment(pyp.Component):
    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # Upper garment
        upper_name = design['meta']['upper']['v']
        Upper = globals()[upper_name]
        self.upper = Upper(body, design)

        # TODO base component
        level_y = self.upper.bbox3D()[0][1]

        # Belt (or not)
        if design['meta']['wb']['v']:
            self.wb = WB(body, design)
            bbox_wb = self.wb.bbox3D()
            
            # Place below the upper garment self.wb.translate_to()   
            self.wb.translate_by([0, level_y - bbox_wb[1][1] - self.wb.width / 2, 0])
            level_y = self.wb.bbox3D()[0][1]

            # TODO Connection is crossing over for T-Shirt. Need to be fixed =(
            self.stitching_rules.append(
                (self.upper.interfaces['bottom'], self.wb.interfaces['top']))

        # Lower garment
        lower_name = design['meta']['bottom']['v']
        Lower = globals()[lower_name]
        self.lower = Lower(body, design)

        # Place below the upper garment or self.wb
        l_level = self.lower.bbox3D()[1][1]
        self.lower.translate_by([0, level_y - l_level, 0])

        # Connect with the garment above
        connect_to = self.wb if design['meta']['wb']['v'] else self.upper

        self.stitching_rules.append(
            (connect_to.interfaces['bottom'], self.lower.interfaces['top']))