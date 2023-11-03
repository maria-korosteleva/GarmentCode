from copy import deepcopy

from assets.garment_programs.skirt_paneled import *
from assets.garment_programs.circle_skirt import *


# TODO Test geometry with different settings
class SkirtLevels(pyp.Component):
    """Skirt constiting of multuple stitched skirts"""

    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        ldesign = design['levels-skirt']
        lbody = deepcopy(body)  # We will modify the values, so need a copy
        n_levels = ldesign['num_levels']['v']
        ruffle = ldesign['level_ruffle']['v']

        base_skirt_class = globals()[ldesign['base']['v']]
        self.subs.append(base_skirt_class(body, design))

        level_skirt_class = globals()[ldesign['level']['v']]

        if (hasattr(base := self.subs[0], 'design')
                and 'low_angle' in base.design):
            angle = base.design['low_angle']['v']
        else:
            angle = 0

        # Place the levels
        for i in range(n_levels):
            top_width = self.subs[-1].interfaces['bottom'].edges.length()
            top_width *= ruffle

            # Adjust the mesurement to trick skirts into producing correct width
            lbody['waist'] = top_width
            self.subs.append(level_skirt_class(lbody, design, tag=str(i)))

            # Placement
            # Rotation if base is assymetric
            self.subs[-1].rotate_by(R.from_euler('XYZ', [0, 0, -angle],
                                                 degrees=True))

            self.subs[-1].place_by_interface(
                self.subs[-1].interfaces['top'],
                self.subs[-2].interfaces['bottom'], 
                gap=5
            )
            # Stitch
            self.stitching_rules.append((
                self.subs[-2].interfaces['bottom'], 
                self.subs[-1].interfaces['top']
            ))

        self.interfaces = {
            'top': self.subs[0].interfaces['top']
        }

