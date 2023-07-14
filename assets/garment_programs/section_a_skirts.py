"""3-section A line skirts: by commertial patterns"""

import numpy as np

# Custom
import pypattern as pyp

# other assets
from .circle_skirt import CircleArcPanel


# DRAFT
class SidePanel(pyp.Panel):

    def __init__(self, name, body, length, side_width, rad, circle_arc=False) -> None:
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

        if not circle_arc:
            right = pyp.Edge(
                [-low_shift, 0],    
                [0, length + adj_hips_depth]  # would ~pass through [hip point, length]
            )

            top = pyp.Edge(right.end, [side_width, length + adj_hips_depth])
            self.edges = pyp.EdgeSequence(
                right, 
                top, 
                pyp.Edge(top.end, [side_width, 0])
            ).close_loop() 

            self.translate_by([0, - length - adj_hips_depth, 0])

            self.interfaces = {
                'bottom': pyp.Interface(self, self.edges[-1]),
                'outside': pyp.Interface(self, right), 
                'inside': pyp.Interface(self, self.edges[-2]),  
                'top': pyp.Interface(self, top)
            }

            
        if circle_arc:   # DRAFT Experiments with different sides
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

        
            self.interfaces = {
                'bottom': pyp.Interface(self, self.edges[-2]),
                'outside': pyp.Interface(self, self.edges[-1]), 
                'inside': pyp.Interface(self, self.edges[-3]),  
                'top': pyp.Interface(self, top)
            }

# TODOLOW More general version of this skirt?
class YokeFlareSection(pyp.Component):
    """Front/back design for Burda 6880 skirt with flared insert"""

    def __init__(self, 
                 name, body, design, dart_position, dart_frac=1., insert_place_shift=0):
        super().__init__(name)

        waist = body['waist'] / 2 
        hips = body['hips'] / 2
        hip_line = body['hips_line']
        adj_hips_depth = hip_line  # Before rise calculations
        # TODO Add rise control? 
        # DRAFT low_width=design['flare']['v'] * body['hips'] / 4
        # DRAFT rise=design['rise']['v']

        length = (
            body['hips_line']  # DRAFT * design['rise']['v'] 
            + design['length']['v'] * body['leg_length']
        )

        # Radius evaluation -- to be used in all elements
        diff = hips - waist
        arc = diff / hip_line
        waist_radius = waist / arc

        # --- One Yoke in-between ---
        # NOTE: the panel is designed to follow the "minimal A-line" skirt
        dart_depth = hip_line * dart_frac
        y_side_length = dart_depth  # it's not exacly the length of dart sides, but ok
        y_top_width = dart_position * 2  # Taken up by the section side

        self.yoke = CircleArcPanel.from_length_rad(
            f'{name}_yoke', 
            y_side_length, y_top_width, waist_radius
        )

        # --- Two side panels ---
        # ~Section of a panel skirt up to a dart
        side_width = (waist - dart_position * 2) / 2
        self.side_right = CircleArcPanel.from_length_rad(
            f'{name}_r_side',
            length + adj_hips_depth, side_width, waist_radius
        ).translate_by([- dart_position * 2 - side_width, 0, 0])
        self.side_left = CircleArcPanel.from_length_rad(
            f'{name}_l_side',
            length + adj_hips_depth, side_width, waist_radius
        ).translate_by([- dart_position * 2 - side_width, 0, 0]).mirror()

        # --- One panel for insert (Circle?) ---
        flare = design['insert_flare']['v']

        in_length = self.side_right.interfaces['left'].edges.length() - y_side_length  # from the length of the inside of side panel
        y_b_width = self.yoke.interfaces['bottom'].edges.length()
        b_rad, _, _ = self.yoke.interfaces['bottom'].edges[0].as_radius_angle()
        b_rad = b_rad / flare

        self.insert = CircleArcPanel.from_length_rad(
            f'{name}_insert',
            in_length, y_b_width, b_rad).translate_by([0, - y_side_length - 2, insert_place_shift])
        
        # --- Connect ---
        self.stitching_rules.append((
            self.yoke.interfaces['bottom'], self.insert.interfaces['top']
        ))

        right_interface = pyp.Interface.from_multiple(
            self.yoke.interfaces['right'], 
            self.insert.interfaces['right']
        )
        self.stitching_rules.append((
            self.side_right.interfaces['left'], right_interface
        ))

        left_interface = pyp.Interface.from_multiple(
            self.yoke.interfaces['left'], 
            self.insert.interfaces['left']
        )
        self.stitching_rules.append((
            self.side_left.interfaces['left'], left_interface
        ))
        

        # --- Interface --- 
        self.interfaces = { 
            'right': self.side_right.interfaces['right'],
            'left': self.side_left.interfaces['right'],
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

# TODO Can I make this skirt with the flare paneled skirt instead?
# TODO Is there a nicer way to add the cuts/stitches?
class CutsSections(pyp.Component):
    """A-line skirt with sections and bottom cuts"""
    def __init__(self, 
                 name, body, design):
        super().__init__(name)

        waist = body['waist'] / 2 
        hips = body['hips'] / 2
        hip_line = body['hips_line']
        adj_hips_depth = hip_line  # Before rise calculations
        # TODO Add rise control? 
        # DRAFT low_width=design['flare']['v'] * body['hips'] / 4
        # DRAFT rise=design['rise']['v']

        length = (
            body['hips_line']  # DRAFT * design['rise']['v'] 
            + design['length']['v'] * body['leg_length']
        )
        cut_depth = design['cut_depth']['v']   # TODO Handle zero cuts

        # Radius evaluation -- to be used in all elements
        diff = hips - waist
        arc = diff / hip_line
        waist_radius = waist / arc

        side_frac = 1/6
        center_frac = 1 - 2 * side_frac

        # ~Sections on the sides
        side_width = waist * side_frac 
        self.side_right = CircleArcPanel.from_length_rad(
            f'{name}_r_side',
            length + adj_hips_depth, side_width, waist_radius
        )
        self.side_left = CircleArcPanel.from_length_rad(
            f'{name}_l_side',
            length + adj_hips_depth, side_width, waist_radius
        ).mirror() 

        # Central panels
        self.center = CircleArcPanel.from_length_rad(
            f'{name}_center',
            length + adj_hips_depth, waist * center_frac, waist_radius
        ).translate_by([0, 0, 0])

        # Placements
        self.side_right.place_by_interface(
            self.side_right.interfaces['left'], 
            self.center.interfaces['right'], 
            gap=10)   # TODO Gap ~= bottom width difference 
        self.side_left.place_by_interface(
            self.side_left.interfaces['left'], 
            self.center.interfaces['left'], 
            gap=10)

        # -- Insert the cuts -- 
        self.insert_cut(self.side_right.interfaces['left'], cut_size=cut_depth)
        self.insert_cut(self.center.interfaces['left'], cut_size=cut_depth)
        self.insert_cut(self.center.interfaces['right'], cut_size=cut_depth)
        self.insert_cut(self.side_left.interfaces['left'], cut_size=cut_depth)

        # --- Connect ---
        self.stitching_rules.append((
            self.side_right.interfaces['left'], self.center.interfaces['right']
        ))
        
        self.stitching_rules.append((
            self.side_left.interfaces['left'], self.center.interfaces['left']
        ))

        # --- Interface --- 
        self.interfaces = { 
            'right': self.side_right.interfaces['right'],
            'left': self.side_left.interfaces['right'],
            'top': pyp.Interface.from_multiple(
                self.side_right.interfaces['top'], 
                self.center.interfaces['top'],
                self.side_left.interfaces['top'], 
            ),
            'bottom': pyp.Interface.from_multiple(
                self.side_right.interfaces['bottom'], 
                self.center.interfaces['bottom'],
                self.side_left.interfaces['bottom'], 
            )
        }

    def insert_cut(self, interface:pyp.Interface, cut_size):
        """Update the edge to have a cut with appropriate interface and panel updates"""
        edge = interface.edges[0]
        panel = interface.panel[0]

        # Correct for edge directions
        flip = edge.start[1] > edge.end[1]  # NOTE: Assumes vertical orientation

        new_edges = edge.subdivide_len([1 - cut_size, cut_size] if flip else [cut_size, 1 - cut_size])
        panel.edges.substitute(edge, new_edges)
        interface.edges.substitute(edge, new_edges[0] if flip else new_edges[1])


# TODO Merge the styles
class SectionALineSkirt(pyp.Component):
    """Based on Burda 6880 style (A-line version with cuts)"""
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['section-skirt']
        self.design = design  # Make accessible from outside

        # TODO Waistband
        # TODO front-back different cuts

        # NOTE: side panels of front and back can be cut together 
        # to avoid introducing side stitch
        self.front = CutsSections(
            f'{self.name}_f', body, design,
            
        ).translate_to([0, body['waist_level'], 25])
        self.back = CutsSections(
            f'{self.name}_b', body, design,
            
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

class SectionALineSkirtFlared(pyp.Component):
    """Based on Burda 6880 style (flare version)"""

    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['section-skirt']
        self.design = design  # Make accessible from outside

        # Depends on leg length
        # condition

        # NOTE: side panels of front and back can be cut together 
        # to avoid introducing side stitch
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