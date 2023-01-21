
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
        if upper_name: 
            Upper = globals()[upper_name]
            self.subs = [Upper(body, design)]

        # Belt (or not)
        if design['meta']['wb']['v']:
            self.subs.append(WB(body, design))

            # Place below the upper garment 
            if len(self.subs) > 1:
                self.subs[-1].place_below(self.subs[-2])

                self.stitching_rules.append(
                    (self.subs[-2].interfaces['bottom'], self.subs[-1].interfaces['top']))

        # Lower garment
        lower_name = design['meta']['bottom']['v']
        if lower_name:
            Lower = globals()[lower_name]
            self.subs.append(Lower(body, design))

            # Place below the upper garment or self.wb
            if len(self.subs) > 1:
                self.subs[-1].place_below(self.subs[-2])

                self.stitching_rules.append(
                    (self.subs[-2].interfaces['bottom'], self.subs[-1].interfaces['top']))