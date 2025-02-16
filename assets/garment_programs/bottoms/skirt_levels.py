from copy import deepcopy

from assets.garment_programs.bottoms import factory
from assets.garment_programs.bottoms.circle_skirt import *
from assets.garment_programs.bottoms.skirt_paneled import *


@factory.register_builder("SkirtLevels")
class SkirtLevels(BaseBottoms):
    """Skirt constiting of multuple stitched skirts"""

    def __init__(self, body: dict, design: dict, rise: float  = None) -> None:
        super().__init__(body, design, rise=rise)

        ldesign = design['levels-skirt']
        lbody = deepcopy(body)  # We will modify the values, so need a copy
        n_levels = ldesign['num_levels']['v']
        ruffle = ldesign['level_ruffle']['v']

        # Adjust length to the common denominators
        self.eval_length(ldesign, body)
        
        # Definitions
        self.rise = ldesign['rise']['v'] if rise is None else rise
        base_skirt_class = globals()[ldesign['base']['v']]
        self.subs.append(base_skirt_class(
            body, 
            design, 
            length=self.base_len, 
            rise=self.rise,
            slit=False))

        if (hasattr(base := self.subs[0], 'design')
                and 'low_angle' in base.design):
            self.angle = base.design['low_angle']['v']
        else:
            self.angle = 0

        # Place the levels
        level_skirt_class = globals()[ldesign['level']['v']]
        for i in range(n_levels):
            # Adjust the mesurement to trick skirts into producing correct width
            # TODOLOW More elegant overwrite
            lbody['waist'] = ruffle * self.subs[-1].interfaces['bottom'].edges.length()
            lbody['waist_back_width'] = ruffle * self.subs[-1].interfaces['bottom_b'].edges.length()
            self.subs.append(level_skirt_class(
                lbody, 
                design, 
                tag=str(i), 
                length=self.level_len, 
                slit=False,
                top_ruffles=False))

            # Placement
            # Rotation if base is assymetric
            self.subs[-1].rotate_by(R.from_euler(
                'XYZ', [0, 0, -self.angle], degrees=True))

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

    def eval_length(self, ldesign, body):
        
        # With convertion to absolute values
        total_length = ldesign['length']['v'] * body['_leg_length']
        self.base_len = total_length * ldesign['base_length_frac']['v']
        self.level_len = (total_length - self.base_len) / ldesign['num_levels']['v']

        # Add hip_line (== zero length)
        self.base_len = body['hips_line'] * ldesign['rise']['v'] + self.base_len
