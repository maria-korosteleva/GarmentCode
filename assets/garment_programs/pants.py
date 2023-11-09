import svgpathtools as svgpath
from copy import deepcopy
import numpy as np

# Custom
import pypattern as pyp

# other assets
from . import bands
from .base_classes import BaseBottoms


# TODO Cuffs
# FIXME Slides too high

class PantPanel(pyp.Panel):
    def __init__(
            self, name, body, design, 
            waist, 
            hips,
            crotch_width,
            dart_position,
            double_dart=False) -> None:
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
        """
        super().__init__(name)

        # FIXME Fix pant width parameter to change appropriately in asymmetric pants
        pant_width = design['width']['v'] * hips 
        length = design['length']['v'] * body['_leg_length']
        flare = design['flare']['v'] 
        # TODO Low width w.r.t. leg_circ??
        low_width = design['width']['v'] * body['hips'] * (flare - 1) / 4  + hips

        hips_depth = body['hips_line']
        hip_side_incl = np.deg2rad(body['hip_inclination'])
        dart_depth = hips_depth * 0.8  # FIXME check

        # Crotch cotrols
        crotch_depth_diff =  body['crotch_hip_diff']
        crotch_extention = crotch_width

        # eval pants shape
        # TODO Return ruffle opportunity?

        # amount of extra fabric at waist
        w_diff = pant_width - waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = np.tan(hip_side_incl) * hips_depth
        # Small difference
        if hw_shift > w_diff:
            hw_shift = w_diff

        # --- Edges definition ---
        # Right
        if pyp.close_enough(flare, 1):  # skip optimization
            right_bottom = pyp.Edge(    
                [hips - low_width, 0], 
                [0, length]
            )
        else:
            right_bottom = pyp.esf.curve_from_tangents(
                [hips - low_width, 0], 
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

        # TODO angled?
        crotch_top = pyp.Edge(
            top.end, 
            [pant_width, length + 0.45 * hips_depth]  # A bit higher than hip line
            # NOTE: The point should be lower than the minimum rise value (0.5)
        )
        crotch_bottom = pyp.esf.curve_from_tangents(
            crotch_top.end,
            [pant_width + crotch_extention, length - crotch_depth_diff], 
            # DRAFT target_tan0=np.array([crotch_extention / 2, - crotch_depth_diff]),
            target_tan0=np.array([0, -1]),
            target_tan1=np.array([1, 0]),
            initial_guess=[0.5, -0.5] 
        )

        # Apply the rise
        # NOTE applying rise here for correctly collecting the edges
        rise = design['rise']['v']
        if not pyp.utils.close_enough(rise, 1.):
            new_level = top.end[1] - (1 - rise) * hips_depth
            right_top, top, crotch_top = self.apply_rise(new_level, right_top, top, crotch_top)

        # TODO same distance from the crotch as in the front 
        left = pyp.esf.curve_from_tangents(
            crotch_bottom.end,    
            [
                # DRAFT min(pant_width, pant_width - (pant_width - low_width) / 2), 
                crotch_bottom.end[0] - 5,   # DRAFT 
                min(0, length - crotch_depth_diff)
            ], 
            target_tan1=np.array([0, -1]),
            initial_guess=[0.3, 0] 
        )

        # DEBUG
        print('Crotch depth: ', abs(top.end[1] - crotch_bottom.end[1]))

        self.edges = pyp.EdgeSequence(
            right_bottom, right_top, top, crotch_top, crotch_bottom, left
            ).close_loop()
        bottom = self.edges[-1]

        # Default placement
        self.set_pivot(crotch_bottom.end)
        self.translation = [-0.5, - hips_depth - crotch_depth_diff + 5, 0] 

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'outside': pyp.Interface(self, pyp.EdgeSequence(right_bottom, right_top)),
            'crotch': pyp.Interface(self, pyp.EdgeSequence(crotch_top, crotch_bottom)),
            'inside': pyp.Interface(self, left),
            'bottom': pyp.Interface(self, bottom)
        }

        # Add top dart 
        dart_width = w_diff - hw_shift   # FIXME Adjust according to rise value (now the original darts are used)
        if w_diff > hw_shift:
            top_edges, int_edges = self.add_darts(
                top, dart_width, dart_depth, dart_position, double_dart=double_dart)
            self.interfaces['top'] = pyp.Interface(self, int_edges) 
            self.edges.substitute(top, top_edges)
        else:
            self.interfaces['top'] = pyp.Interface(self, top) 

    def apply_rise(self, level, right, top, crotch):

        # TODOLOW This could be an operator or edge function
        right_c, crotch_c = right.as_curve(), crotch.as_curve()
        ext = 5  # Extend cutout a bit for stable intersection results
        cutout = svgpath.Line(0 + 1j*level, crotch.end[0] + ext + 1j*level)

        right_intersect = right_c.intersect(cutout)[0]
        right_cut = right_c.cropped(0, right_intersect[0])
        new_right = pyp.CurveEdge.from_svg_curve(right_cut)

        c_intersect = crotch_c.intersect(cutout)[0]
        c_cut = crotch_c.cropped(c_intersect[0], 1)

        new_crotch = pyp.Edge.from_svg_curve(c_cut)

        new_top = pyp.Edge(new_right.end, new_crotch.start)

        return new_right, new_top, new_crotch


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

            print(dart_position, dist)
        else:
            offsets_mid = [
                - dart_position - dart_width / 2,
            ]
            darts = [
                pyp.esf.dart_shape(dart_width, dart_depth)
            ]
        top_edges, int_edges = pyp.EdgeSequence(top), pyp.EdgeSequence(top)

        # DEBUG
        print('Pants ', offsets_mid)

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
        

class PantsHalf(pyp.Component):
    def __init__(self, tag, body, design) -> None:
        super().__init__(tag)
        design = design['pants']


        # NOTE: min value = full sum > leg curcumference
        # Max: pant leg falls flat from the back
        # Mostly from the back side
        # => This controls the foundation width of the pant
        min_ext = body['leg_circ'] - body['hips'] / 2 + 5  # 2 inch "ease"
        max_ext = 22  # Measured max
        tmp_width = 0.2
        front_frac = 0.4   # 0.3 = 6.5 = front/4 for the max width, 0.4 = 6.5 for 0.5

        # DEBUG
        print('min ext', min_ext)

        # DEBUG Note: measurement for the crotch width is 22/25
        front_hip = (body['hips'] - body['hip_back_width']) / 2
        crotch_extention = max_ext * tmp_width + (1 - tmp_width) * min_ext  # DRAFT  16 # 22 -- culotte   
        front_extention = front_frac * crotch_extention  # DRAFT front_hip / 4  #  
        back_extention = crotch_extention - front_extention

         # DEBUG
        print('Crotch extention ', crotch_extention, front_extention, back_extention)
        print('Crotch extention ', front_extention / crotch_extention, back_extention / crotch_extention)

        self.front = PantPanel(
            f'pant_f_{tag}', body, design,
            waist=(body['waist'] - body['waist_back_width']) / 2,
            hips=(body['hips'] - body['hip_back_width']) / 2,
            dart_position = body['bust_points'] / 2,
            crotch_width=front_extention,
            ).translate_by([0, body['_waist_level'] - 5, 25])
        self.back = PantPanel(
            f'pant_b_{tag}', body, design,
            waist=body['waist_back_width'] / 2,
            hips=body['hip_back_width'] / 2,
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
        super().__init__('Pants')

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

        # DEBUG
        print('Waist len: ', self.interfaces['top'].edges.length())

    def get_rise(self):
        return self.design['pants']['rise']['v']

