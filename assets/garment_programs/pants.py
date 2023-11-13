from copy import deepcopy
import numpy as np

# Custom
import pypattern as pyp

# other assets
from . import bands
from .base_classes import BaseBottoms


class PantPanel(pyp.Panel):
    def __init__(
            self, name, body, design, 
            length,
            waist, 
            hips,
            hips_depth,
            crotch_width,
            dart_position,
            hipline_ext=1,
            double_dart=False) -> None:
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
        """
        super().__init__(name)

        flare = body['leg_circ'] * (design['flare']['v']  - 1) / 4 
        hips_depth = hips_depth * hipline_ext

        hip_side_incl = np.deg2rad(body['hip_inclination'])
        dart_depth = hips_depth * 0.8 

        # Crotch cotrols
        crotch_depth_diff =  body['crotch_hip_diff']
        crotch_extention = crotch_width

        # eval pants shape
        # TODO Return ruffle opportunity?

        # amount of extra fabric at waist
        w_diff = hips - waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = np.tan(hip_side_incl) * hips_depth
        # Small difference
        if hw_shift > w_diff:
            hw_shift = w_diff

        # --- Edges definition ---
        # Right
        if pyp.close_enough(design['flare']['v'], 1):  # skip optimization
            right_bottom = pyp.Edge(    
                [-flare, 0], 
                [0, length]
            )
        else:
            right_bottom = pyp.esf.curve_from_tangents(
                [-flare, 0], 
                [0, length],
                target_tan1=np.array([0, 1]), 
                # initial guess places control point closer to the hips 
                initial_guess=[0.75, 0]
            )
        right_top = pyp.esf.curve_from_tangents(
            right_bottom.end,    
            [hw_shift, length + hips_depth],
            target_tan0=np.array([0, 1]),
            initial_guess=[0.5, 0] 
        )
       
        top = pyp.Edge(
            right_top.end, 
            [w_diff + waist, length + hips_depth] 
        )

        crotch_top = pyp.Edge(
            top.end, 
            [hips, length + 0.45 * hips_depth]  # A bit higher than hip line
            # NOTE: The point should be lower than the minimum rise value (0.5)
        )
        crotch_bottom = pyp.esf.curve_from_tangents(
            crotch_top.end,
            [hips + crotch_extention, length - crotch_depth_diff], 
            target_tan0=np.array([0, -1]),
            target_tan1=np.array([1, 0]),
            initial_guess=[0.5, -0.5] 
        )

        left = pyp.esf.curve_from_tangents(
            crotch_bottom.end,    
            [
                # NOTE "Magic value" which we use to define default width:
                #   just a little behing the crotch point
                # NOTE: Ensuring same distance from the crotch point in both 
                #   front and back for matching curves
                crotch_bottom.end[0] - 2 + flare, 
                y:=min(0, length - crotch_depth_diff)
            ], 
            target_tan1=[flare, y - crotch_bottom.end[1]],
            initial_guess=[0.3, 0]
        )

        self.edges = pyp.EdgeSequence(
            right_bottom, right_top, top, crotch_top, crotch_bottom, left
            ).close_loop()
        bottom = self.edges[-1]

        # Default placement
        self.set_pivot(crotch_bottom.end)
        self.translation = [-0.5, - hips_depth - crotch_depth_diff + 5, 0] 

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'outside': pyp.Interface(
                self, 
                pyp.EdgeSequence(right_bottom, right_top), 
                ruffle=[1, hipline_ext]),
            'crotch': pyp.Interface(self, pyp.EdgeSequence(crotch_top, crotch_bottom)),
            'inside': pyp.Interface(self, left),
            'bottom': pyp.Interface(self, bottom)
        }

        # Add top dart 
        dart_width = w_diff - hw_shift  
        if w_diff > hw_shift:
            top_edges, int_edges = self.add_darts(
                top, dart_width, dart_depth, dart_position, double_dart=double_dart)
            self.interfaces['top'] = pyp.Interface(self, int_edges) 
            self.edges.substitute(top, top_edges)
        else:
            self.interfaces['top'] = pyp.Interface(self, top) 

    def add_darts(self, top, dart_width, dart_depth, dart_position, double_dart=False):
        
        if double_dart:
            # TODOLOW Avoid hardcoding for matching with the top?
            dist = dart_position * 0.5  # Dist between darts -> dist between centers
            offsets_mid = [
                - (dart_position + dist / 2 + dart_width / 2 + dart_width / 4),   
                - (dart_position - dist / 2) - dart_width / 4,
            ]

            darts = [
                pyp.esf.dart_shape(dart_width / 2, dart_depth * 0.9), # smaller
                pyp.esf.dart_shape(dart_width / 2, dart_depth)  
            ]
        else:
            offsets_mid = [
                - dart_position - dart_width / 2,
            ]
            darts = [
                pyp.esf.dart_shape(dart_width, dart_depth)
            ]
        top_edges, int_edges = pyp.EdgeSequence(top), pyp.EdgeSequence(top)

        for off, dart in zip(offsets_mid, darts):
            left_edge_len = top_edges[-1].length()
            top_edges, int_edges = self.add_dart(
                dart,
                top_edges[-1],
                offset=left_edge_len + off,
                edge_seq=top_edges, 
                int_edge_seq=int_edges
            )

        return top_edges, int_edges
        

class PantsHalf(BaseBottoms):
    def __init__(self, tag, body, design) -> None:
        super().__init__(body, design, tag)
        design = design['pants']
        waist, hips_depth, waist_back = self.eval_rise(design['rise']['v'])

        # NOTE: min value = full sum > leg curcumference
        # Max: pant leg falls flat from the back
        # Mostly from the back side
        # => This controls the foundation width of the pant
        min_ext = body['leg_circ'] - body['hips'] / 2  + 5  # 2 inch ease: from pattern making book 
        front_hip = (body['hips'] - body['hip_back_width']) / 2
        crotch_extention = min_ext * design['width']['v']  
        front_extention = front_hip / 4    # From pattern making book
        back_extention = crotch_extention - front_extention

        length = design['length']['v'] * body['_leg_length']
        cuff_len = design['cuff']['cuff_len']['v'] * body['_leg_length']
        if design['cuff']['type']['v'] and length > cuff_len:
            # Include the cuff into the overall length, 
            # unless the requested length is too short to fit the cuff 
            # (to avoid negative length)
            length -= cuff_len

        self.front = PantPanel(
            f'pant_f_{tag}', body, design,
            length=length,
            waist=(waist - waist_back) / 2,
            hips=(body['hips'] - body['hip_back_width']) / 2,
            hips_depth=hips_depth,
            dart_position = body['bust_points'] / 2,
            crotch_width=front_extention,
            ).translate_by([0, body['_waist_level'] - 5, 25])
        self.back = PantPanel(
            f'pant_b_{tag}', body, design,
            length=length,
            waist=waist_back / 2,
            hips=body['hip_back_width'] / 2,
            hips_depth=hips_depth,
            hipline_ext=1.1,
            dart_position = body['bum_points'] / 2,
            crotch_width=back_extention,
            double_dart=True
            ).translate_by([0, body['_waist_level'] - 5, -20])

        self.stitching_rules = pyp.Stitches(
            (self.front.interfaces['outside'], self.back.interfaces['outside']),
            (self.front.interfaces['inside'], self.back.interfaces['inside'])
        )

        # add a cuff
        # TODOLOW This process is the same for sleeves -- make a function?
        if design['cuff']['type']['v']:
            
            pant_bottom = pyp.Interface.from_multiple(
                    self.front.interfaces['bottom'], self.back.interfaces['bottom'])

            # Copy to avoid editing original design dict
            cdesign = deepcopy(design)
            cdesign['cuff']['b_width'] = {}
            cdesign['cuff']['b_width']['v'] = pant_bottom.edges.length() / design['cuff']['top_ruffle']['v']
            cdesign['cuff']['cuff_len']['v'] = design['cuff']['cuff_len']['v'] * body['_leg_length']

            # Init
            cuff_class = getattr(bands, cdesign['cuff']['type']['v'])
            self.cuff = cuff_class(tag, cdesign)

            # Position
            self.cuff.place_by_interface(
                self.cuff.interfaces['top'],
                pant_bottom,
                gap=5
            )

            # Stitch
            self.stitching_rules.append((
                pant_bottom,
                self.cuff.interfaces['top'])
            )

        self.interfaces = {
            'crotch_f': self.front.interfaces['crotch'],
            'crotch_b': self.back.interfaces['crotch'],
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
        }

class Pants(BaseBottoms):
    def __init__(self, body, design) -> None:
        super().__init__(body, design)

        self.right = PantsHalf('r', body, design)
        self.left = PantsHalf('l', body, design).mirror()

        self.stitching_rules = pyp.Stitches(
            (self.right.interfaces['crotch_f'], self.left.interfaces['crotch_f']),
            (self.right.interfaces['crotch_b'], self.left.interfaces['crotch_b']),
        )

        self.interfaces = {
            'top_f': pyp.Interface.from_multiple(
                self.right.interfaces['top_f'], self.left.interfaces['top_f']),
            'top_b': pyp.Interface.from_multiple(
                self.right.interfaces['top_b'], self.left.interfaces['top_b']),
            # Some are reversed for correct connection
            'top': pyp.Interface.from_multiple(   # around the body starting from front right
                self.right.interfaces['top_f'],
                self.left.interfaces['top_f'].reverse(),
                self.left.interfaces['top_b'],   
                self.right.interfaces['top_b'].reverse()),
        }

    def get_rise(self):
        return self.design['pants']['rise']['v']

