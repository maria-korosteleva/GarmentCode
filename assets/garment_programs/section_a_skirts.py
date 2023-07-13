"""3-section A line skirts: by commertial patterns"""

from scipy.spatial.transform import Rotation as R
import numpy as np

# Custom
import pypattern as pyp

# other assets
from .bands import WB
from . import shapes
from .circle_skirt import CircleArcPanel
from .skirt_paneled import SkirtPanel


# TODO
class SidePanel(pyp.Panel):

    def __init__(self, name, body, length, side_width, rad) -> None:
        super().__init__(name)

        waist = body['waist'] / 4 
        hips = body['hips'] / 4
        hip_line = body['hips_line']
        adj_hips_depth = hip_line  # TODO support of rise goes here

        wdiff = hips - waist
        hw_shift = wdiff / 6   # NOTE would be less

        low_shift = hw_shift * (length + adj_hips_depth) / hip_line   # just elongation from the hip to the bottom with the same angle
        low_width = side_width + low_shift

        # DEBUG
        print('Bottom width: ', low_shift, length, side_width, hips)
        # print('Bottom angle: ', np.rad2deg(np.arctan(tan)), low_w2)

        # DRAFT right = pyp.Edge(
        #     [-low_shift, 0],    
        #     [0, length + adj_hips_depth]  # would ~pass through [hip point, length]
        # )

        # # TODO curve!
        # top = pyp.Edge(right.end, [side_width, length + adj_hips_depth])
        
        top = pyp.CircleEdge.from_rad_length(
            rad=rad, length=side_width
        )

        vert_len = np.sqrt((length + adj_hips_depth)**2 - (low_width / 2 - top.end[0]))
        left = pyp.Edge(top.end, [low_width / 2, -vert_len])
        
        # Bottom with a little curve
        bottom = pyp.CircleEdge(
            left.end, [- low_width / 2, -vert_len], 
            cy=0.05)

        self.edges = pyp.EdgeSequence(
            top, 
            left, 
            bottom
        ).close_loop() 

        # DRAFT self.edges = pyp.EdgeSequence(
        #     right, 
        #     top, 
        #     pyp.Edge(top.end, [side_width, 0])
        # ).close_loop()  # TODO curve the bottom a little

        

        #DRAFT self.translate_by([0, - length - adj_hips_depth, 0])

        self.interfaces = {
            'bottom': pyp.Interface(self, self.edges[-2]),
            'outside': pyp.Interface(self, self.edges[-1]), 
            'inside': pyp.Interface(self, self.edges[-3]),  
            'top': pyp.Interface(self, top)
        }

class YokeFlareSection(pyp.Component):
    """Front/back design for Burda 6880 skirt with flared insert"""

    def __init__(self, name, body, design, dart_position, dart_frac=1., insert_place_shift=0):
        super().__init__(name)

        waist = body['waist'] / 2 
        hips = body['hips'] / 2
        hip_line = body['hips_line']
        adj_hips_depth = hip_line  # Before rise calculations
        # DRAFT low_width=design['flare']['v'] * body['hips'] / 4
        # DRAFT rise=design['rise']['v']   # TODO Add rise control? 

        length = (
            body['hips_line'] * design['rise']['v'] 
            + design['length']['v'] * body['leg_length']
        )

        # --- One Yoke in-between ---
        # DEBUG Flat section (for testing)
        # NOTE: the differentce is by the desired "dart" angle in a way
        dart_w = (hips - waist) / 2 * 5 / 6
        dart_depth = hip_line * dart_frac
        # DRAFT for the adjustible rise dart_depth = max(dart_depth - (hip_line - adj_hips_depth), 0)
        y_side_length = dart_depth  # TODO it's not exacly the length of dart sides, but ok
        y_top_width = dart_position * 2  # Taken up by the section side
        y_b_width = y_top_width + 2 * dart_w  # TODO length between the dart bottoms

        self.yoke = CircleArcPanel.from_all_length(
            f'{name}_yoke', y_side_length, y_top_width, y_b_width
            )

        # --- Two side panels ---
        # ~Section of a panel skirt up to a dart
        side_width = (waist - dart_position * 2) / 2
        top_rad, _, _ = self.yoke.interfaces['top'].edges[0].as_radius_angle()
        self.side_right = SidePanel(
            f'{name}_r_side',
            body, length, side_width, top_rad
        ).translate_by([- dart_position * 2 - side_width, 0, 0])
        self.side_left = SidePanel(
            f'{name}_l_side',
            body, length, side_width, top_rad
        ).translate_by([- dart_position * 2 - side_width, 0, 0]).mirror()

        # self.side_right = CircleArcPanel.from_length_rad(
        #     f'{name}_r_side',
        #     length + adj_hips_depth, side_width, top_rad
        # ).translate_by([- dart_position * 2 - side_width, 0, 0])
        # self.side_left = CircleArcPanel.from_length_rad(
        #     f'{name}_l_side',
        #     length + adj_hips_depth, side_width, top_rad
        # ).translate_by([- dart_position * 2 - side_width, 0, 0]).mirror()


        # --- One panel for insert (Circle?) ---
        suns = 0.3  # TODO parameter -- use flare parameter instead, s.t no flare == classic A-line skirt?
        in_length = self.side_right.interfaces['inside'].edges.length() - y_side_length  # from the length of the inside of side panel
        self.insert = CircleArcPanel.from_w_length_suns(
            f'{name}_insert',
            in_length, y_b_width, suns / 2).translate_by([0, 0, insert_place_shift])
        
        # --- Connect ---
        self.stitching_rules.append((
            self.yoke.interfaces['bottom'], self.insert.interfaces['top']
        ))

        right_interface = pyp.Interface.from_multiple(
            self.yoke.interfaces['right'], 
            self.insert.interfaces['right']
        )
        self.stitching_rules.append((
            self.side_right.interfaces['inside'], right_interface
        ))

        left_interface = pyp.Interface.from_multiple(
            self.yoke.interfaces['left'], 
            self.insert.interfaces['left']
        )
        self.stitching_rules.append((
            self.side_left.interfaces['inside'], left_interface
        ))
        

        # --- Interface --- 
        self.interfaces = { # TODO Add top and bottom
            'right': self.side_right.interfaces['outside'],
            'left': self.side_left.interfaces['outside'],
            'top': pyp.Interface.from_multiple(
                self.side_right.interfaces['top'], 
                self.yoke.interfaces['top'],
                self.side_left.interfaces['top'], 
            ),
            'bottom': pyp.Interface.from_multiple(
                self.side_right.interfaces['bottom'], 
                self.insert.interfaces['bottom'],
                self.side_left.interfaces['bottom'], 
            )
        }




class SectionALineSkirt(pyp.Component):

    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['pencil-skirt']
        self.design = design  # Make accessible from outside

        # Depends on leg length
        # condition

        # TODO Side panels are one panel??

        self.front = YokeFlareSection(
            f'{self.name}_f', body, design,
            dart_position=body['bust_points'] / 2,
            dart_frac=0.9,  # Diff for front and back
            insert_place_shift=10
        ).translate_to([0, body['waist_level'], 25])
        self.back = YokeFlareSection(
            f'{self.name}_b', body, design,
            dart_position=body['bum_points'] / 2,
            dart_frac=0.8,   
            insert_place_shift=-10
        ).translate_to([0, body['waist_level'], -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyp.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top'].reverse()
            ),
            'bottom': pyp.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }