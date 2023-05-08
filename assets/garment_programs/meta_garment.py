
""" A Meta garment component!
    Depending on parameter values it can generate sewing patterns 
    for various dresses and jumpsuit styles and fit them to the body measurements
"""

# Custom
import pypattern as pyp

from assets.garment_programs.skirt_paneled import *
from assets.garment_programs.circle_skirt import *
from assets.garment_programs.skirt_levels import *
from assets.garment_programs.tee import *
from assets.garment_programs.godet import *
from assets.garment_programs.bodice import *
from assets.garment_programs.pants import *
from assets.garment_programs.bands import *
from assets.garment_programs.sleeves import *
from assets.garment_programs.random_tests import *  # DEBUG 


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
                self.subs[-1].place_by_interface(
                    self.subs[-1].interfaces['top'],
                    self.subs[-2].interfaces['bottom'], 
                    gap=3
                )

                self.stitching_rules.append(
                    (self.subs[-2].interfaces['bottom'], self.subs[-1].interfaces['top']))

        # Lower garment
        lower_name = design['meta']['bottom']['v']
        if lower_name:
            Lower = globals()[lower_name]
            self.subs.append(Lower(body, design))

            # Place below the upper garment or self.wb
            if len(self.subs) > 1:
                self.subs[-1].place_by_interface(
                    self.subs[-1].interfaces['top'],
                    self.subs[-2].interfaces['bottom'], 
                    gap=3
                )
                self.stitching_rules.append(
                    (self.subs[-2].interfaces['bottom'], self.subs[-1].interfaces['top']))