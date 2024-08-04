import numpy as np
from scipy.spatial.transform import Rotation as R

import pygarment as pyg
from assets.garment_programs.base_classes import StackableSkirtComponent
from assets.garment_programs.base_classes import BaseBottoms
from assets.garment_programs import shapes


class SkirtPanel(pyg.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, 
                 name, 
                 waist_length=70, length=70, 
                 ruffles=1,
                 match_top_int_to=None,
                 bottom_cut=0, 
                 flare=0
        ) -> None:
        super().__init__(name)

        base_width = waist_length
        top_width = base_width * ruffles
        low_width = top_width + 2*flare
        x_shift_top = (low_width - top_width) / 2  # to account for flare at the bottom

        # define edge loop
        self.right = pyg.EdgeSeqFactory.side_with_cut(
            [0, 0],
            [x_shift_top, length],
            start_cut=bottom_cut / length) if bottom_cut else pyg.EdgeSequence(
            pyg.Edge([0, 0], [x_shift_top, length]))
        self.waist = pyg.Edge(
            self.right[-1].end, [x_shift_top + top_width, length])
        self.left = pyg.EdgeSeqFactory.side_with_cut(
            self.waist.end, [low_width, 0],
            end_cut=bottom_cut / length) if bottom_cut else pyg.EdgeSequence(
            pyg.Edge(self.waist.end, [low_width, 0]))
        self.bottom = pyg.Edge(self.left[-1].end, self.right[0].start)
        
        # define interface
        self.interfaces = {
            'right': pyg.Interface(self, self.right[-1]),
            'top': pyg.Interface(self, self.waist,
                                 ruffle=self.waist.length() / match_top_int_to if match_top_int_to is not None else ruffles
            ).reverse(True),
            'left': pyg.Interface(self, self.left[0]),
            'bottom': pyg.Interface(self, self.bottom)
        }
        # Single sequence for correct assembly
        self.edges = self.right
        self.edges.append(self.waist)  # on the waist
        self.edges.append(self.left)
        self.edges.append(self.bottom)

        # default placement
        self.top_center_pivot()
        self.center_x()  # Already know that this panel should be centered over Y


class ThinSkirtPanel(pyg.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10, bottom_width=20, length=70, b_curvature=0) -> None:
        super().__init__(name)

        # define edge loop
        self.flare = (bottom_width - top_width) / 2
        self.edges = pyg.EdgeSeqFactory.from_verts(
            [0, 0], [self.flare, length], [self.flare + top_width, length],
            [self.flare * 2 + top_width, 0])

        if pyg.utils.close_enough(b_curvature, 0):
            self.edges.close_loop()
        else:
            self.edges.append(
                pyg.CircleEdgeFactory.from_three_points(
                    self.edges[-1].end,
                    self.edges[0].start,
                    [0.5, b_curvature], 
                    relative=True  
                )
            )

        # w.r.t. top left point
        self.set_pivot(self.edges[0].end)

        self.interfaces = {
            'right': pyg.Interface(self, self.edges[0]),
            'top': pyg.Interface(self, self.edges[1]),
            'left': pyg.Interface(self, self.edges[2]),
            'bottom': pyg.Interface(self, self.edges[-1])
        }


class FittedSkirtPanel(pyg.Panel):
    """Fitted panel for a pencil skirt"""
    def __init__(
            self, name, body, design, 
            waist, hips, hips_depth,  # TODOLOW Half measurement instead of a quarter   
            length,
            hipline_ext=1,
            dart_position=None, dart_frac=0.5, double_dart=False,
            match_top_int_to=None,
            slit=0, left_slit=0, right_slit=0,
            side_cut=None, flip_side_cut=False
        ) -> None:
        """ Fitted panel for a pencil skirt

            Body/design values that differ between front and back panels are supplied as parameters, 
            the rest are taken from the body and design dictionaries
        """
        super().__init__(name)

        # Shared params
        low_angle = design['low_angle']['v']
        hip_side_incl = np.deg2rad(body['_hip_inclination'])
        flare = design['flare']['v']
        low_width = body['hips'] * (flare - 1) / 4 + hips  # Distribute the difference equally 
                                                                           # between front and back
        # adjust for a rise
        adj_hips_depth = hips_depth * hipline_ext
        dart_depth = hips_depth * dart_frac
        dart_depth = max(dart_depth - (hips_depth - adj_hips_depth), 0)

        # amount of extra fabric
        w_diff = hips - waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = np.tan(hip_side_incl) * adj_hips_depth
        # Small difference
        if hw_shift > w_diff:
            hw_shift = w_diff

        # Adjust the bottom edge to the desired angle
        angle_shift = np.tan(np.deg2rad(low_angle)) * low_width

        # --- Edges definition ---
        # Right
        if pyg.utils.close_enough(flare, 1):  # skip optimization
            right_bottom = pyg.Edge(    
                [hips - low_width, angle_shift], 
                [0, length]
            )
        else:
            right_bottom = pyg.CurveEdgeFactory.curve_from_tangents(
                [hips - low_width, angle_shift], 
                [0, length],
                target_tan1=np.array([0, 1]), 
                # initial guess places control point closer to the hips 
                initial_guess=[0.75, 0]
            )
        right_top = pyg.CurveEdgeFactory.curve_from_tangents(
            right_bottom.end,
            [hw_shift, length + adj_hips_depth],
            target_tan0=np.array([0, 1]),
            initial_guess=[0.5, 0] 
        )
        right = pyg.EdgeSequence(right_bottom, right_top)

        # top
        top = pyg.Edge(right[-1].end, [hips * 2 - hw_shift, length + adj_hips_depth])

        # left
        left_top = pyg.CurveEdgeFactory.curve_from_tangents(
            top.end,    
            [hips * 2, length],
            target_tan1=np.array([0, -1]),
            initial_guess=[0.5, 0]
        )
        if pyg.utils.close_enough(flare, 1):  # skip optimization for straight skirt
            left_bottom = pyg.Edge(  
                left_top.end, 
                [hips + low_width, -angle_shift], 
            )
        else:
            left_bottom = pyg.CurveEdgeFactory.curve_from_tangents(  
                left_top.end, 
                [hips + low_width, -angle_shift], 
                target_tan0=np.array([0, -1]),
                # initial guess places control point closer to the hips 
                initial_guess=[0.25, 0]  
            )
        left = pyg.EdgeSequence(left_top, left_bottom)

        # fin
        self.edges = pyg.EdgeSequence(right, top, left).close_loop()
        bottom = self.edges[-1]

        if slit:  # add a slit
            # Use long and thin disconnected dart for a cutout
            new_edges, _, int_edges = pyg.ops.cut_into_edge(
                pyg.EdgeSeqFactory.dart_shape(2, depth=slit * length),  # a very thin cutout
                bottom, 
                offset=bottom.length() / 2,
                right=True)

            self.edges.substitute(bottom, new_edges)
            bottom = int_edges
        
        if left_slit:
            frac = left_slit
            new_left_bottom = left_bottom.subdivide_len([1 - frac, frac])
            left.substitute(left_bottom, new_left_bottom[0])
            self.edges.substitute(left_bottom, new_left_bottom)
            left_bottom = new_left_bottom[0]
        
        if right_slit:
            frac = right_slit
            new_rbottom = right_bottom.subdivide_len([frac, 1 - frac])
            right.substitute(right_bottom, new_rbottom[1])
            self.edges.substitute(right_bottom, new_rbottom)
            right_bottom = new_rbottom[1]

        if side_cut is not None:
            try:
                # Add a stylistic cutout to the skirt
                new_edges, _, int_edges = pyg.ops.cut_into_edge(
                    side_cut, left_bottom, 
                    offset=left_bottom.length() / 2, 
                    right=True, flip_target=flip_side_cut)
            except:
                # Skip adding the cut if it doesn't fit (e.g. because of the slit)
                pass
            else:
                self.edges.substitute(left_bottom, new_edges)
                left.substitute(left_bottom, new_edges)

        # Default placement
        self.top_center_pivot()
        self.translation = [-hips / 2, 5, 0]

        # Out interfaces (easier to define before adding a dart)
        # Adding ruffle factor on the hip line extention (used in back panel)
        self.interfaces = {
            'bottom': pyg.Interface(self, bottom),
            'right': pyg.Interface(self, right, [1] * (len(right) - 1) + [hipline_ext]), 
            'left': pyg.Interface(self, left, [hipline_ext] + [1] * (len(left) - 1)),  
        }
        self.interfaces['left'].edges_flipping[0] = True
        self.interfaces['right'].edges_flipping[-1] = True

        # Add top darts
        if w_diff > hw_shift:
            dart_width = w_diff - hw_shift
            top_edges, int_edges = self.add_darts(top, dart_width, dart_depth, dart_position, double_dart=double_dart)

            self.interfaces['top'] = pyg.Interface(
                self, int_edges,
                ruffle=int_edges.length() / match_top_int_to if match_top_int_to is not None else 1.
            ) 
            self.edges.substitute(top, top_edges)
        else:
            self.interfaces['top'] = pyg.Interface(
                self, top,
                ruffle=top.length() / match_top_int_to if match_top_int_to is not None else 1.
            ) 

    def add_darts(self, top, dart_width, dart_depth, dart_position, double_dart=False):
        top_edge_len = top.length()
        if double_dart:
            # TODOLOW Avoid hardcoding for matching with the top?
            dist = dart_position * 0.5    # Dist between darts -> dist between centers
            offsets_mid = [
                - (dart_position + dist / 2 + dart_width / 2) - dart_width / 4,   
                - (dart_position - dist / 2) - dart_width / 4,
                dart_position - dist / 2 + dart_width / 4,
                dart_position + dist / 2 + dart_width / 2 + dart_width / 4,
            ]

            # dart_shape = pyp.EdgeSeqFactory.dart_shape(dart_width, dart_depth)
            dart_shape_full = pyg.EdgeSeqFactory.dart_shape(dart_width / 2, dart_depth)
            dart_shape_small = pyg.EdgeSeqFactory.dart_shape(dart_width / 2, dart_depth * 0.9)
            darts = [
                dart_shape_small, 
                dart_shape_full, 
                dart_shape_full, 
                dart_shape_small, 
            ]
        else:
            offsets_mid = [
                - dart_position - dart_width / 2,
                dart_position + dart_width / 2,
            ]

            dart_shape = pyg.EdgeSeqFactory.dart_shape(dart_width, dart_depth)
            darts = [
                dart_shape, 
                dart_shape, 
            ]
        top_edges, int_edges = pyg.EdgeSequence(top), pyg.EdgeSequence(top)

        for off, dart in zip(offsets_mid, darts):
            left_edge_len = top_edges[-1].length()
            top_edges, int_edges = self.add_dart(
                dart,
                top_edges[-1],
                offset=(left_edge_len - top_edge_len / 2) + off,
                edge_seq=top_edges, 
                int_edge_seq=int_edges
            )

        return top_edges, int_edges


# Full garments - Components
class PencilSkirt(StackableSkirtComponent):
    def __init__(self, body, design, tag='', length=None, rise=None, slit=True, **kwargs) -> None:
        super().__init__(body, design, tag)

        design = design['pencil-skirt']
        self.design = design  # Make accessible from outside

        # condition
        if design['style_side_cut']['v'] is not None:
            depth = 0.7 * (body['hips'] / 4 - body['bust_points'] / 2)
            shape_class = getattr(shapes, design['style_side_cut']['v'])
            style_shape_l, style_shape_r = shape_class(
                width=depth * 1.5, 
                depth=depth, n_rays=6, d_rays=depth*0.2,
                filename=design['style_side_file']['v'] if 'style_side_file' in design else None
            )
        else:
            style_shape_l, style_shape_r = None, None

        # Force from arguments if given
        self.rise = design['rise']['v'] if rise is None else rise
        waist, hips_depth, back_waist = self.eval_rise(self.rise)
        if length is None:
            length = design['length']['v'] * body['_leg_length']  # Depends on leg length
        else:
            length = length - hips_depth

        self.front = FittedSkirtPanel(
            'skirt_front',   
            body,
            design,
            (waist - back_waist) / 2,
            (body['hips'] - body['hip_back_width']) / 2,
            hips_depth=hips_depth,
            length=length,
            dart_position=body['bust_points'] / 2,
            dart_frac=0.8,  # Diff for front and back
            match_top_int_to=(body['waist'] - body['waist_back_width']),
            slit=design['front_slit']['v'] if slit else 0, 
            left_slit=design['left_slit']['v'] if slit else 0,
            right_slit=design['right_slit']['v'] if slit else 0,
            side_cut=style_shape_l
        ).translate_to([0, body['_waist_level'], 25])

        self.back = FittedSkirtPanel(
            'skirt_back', 
            body,
            design,
            back_waist / 2,
            body['hip_back_width'] / 2,
            length=length,
            hips_depth=hips_depth,
            hipline_ext=1.05,
            dart_position=body['bum_points'] / 2,
            dart_frac=0.85,   
            double_dart=True,
            match_top_int_to=body['waist_back_width'],
            slit=design['back_slit']['v'] if slit else 0, 
            left_slit=design['left_slit']['v'] if slit else 0, 
            right_slit=design['right_slit']['v'] if slit else 0,
            side_cut=style_shape_r, 
            flip_side_cut=False,
        ).translate_to([0, body['_waist_level'], -20])

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'].flip_edges(),
                self.back.interfaces['top'].reverse(with_edge_dir_reverse=True)
            ),
            'bottom_f': self.front.interfaces['bottom'],
            'bottom_b': self.back.interfaces['bottom'],
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }

    def length(self):
        return self.front.length()

class Skirt2(StackableSkirtComponent):
    """Simple 2 panel skirt"""
    def __init__(self, body, design, tag='', length=None, rise=None, slit=True, top_ruffles=True, min_len=5) -> None:
        super().__init__(body, design, tag)

        design = design['skirt']

        self.rise = design['rise']['v'] if rise is None else rise
        waist, hip_line, back_waist = self.eval_rise(self.rise)

        # Force from arguments if given
        if length is None:
            length = hip_line + design['length']['v'] * body['_leg_length']  # Depends on leg length

        # NOTE: with some combinations of rise and length parameters length may become too small/negative
        # Hence putting a min positive value here
        length = max(length, min_len)

        self.front = SkirtPanel(
            f'skirt_front_{tag}' if tag else 'skirt_front', 
            waist_length=waist - back_waist, 
            length=length,
            ruffles=design['ruffle']['v'] if top_ruffles else 1,   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v'] * design['length']['v'] if slit else 0,
            match_top_int_to=(body['waist'] - body['waist_back_width'])
        ).translate_to([0, body['_waist_level'], 25])
        self.back = SkirtPanel(
            f'skirt_back_{tag}'  if tag else 'skirt_back', 
            waist_length=back_waist, 
            length=length,
            ruffles=design['ruffle']['v'] if top_ruffles else 1,   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v'] * design['length']['v'] if slit else 0,
            match_top_int_to=body['waist_back_width']
        ).translate_to([0, body['_waist_level'], -20])

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']
            ),
            'bottom_f': self.front.interfaces['bottom'],
            'bottom_b': self.back.interfaces['bottom'],
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }

    def length(self):
        return self.front.length()


class SkirtManyPanels(BaseBottoms):
    """Round Skirt with many panels"""

    def __init__(self, body, design, tag='', rise=None, min_len=5) -> None:
        tag_extra = str(design['flare-skirt']['skirt-many-panels']['n_panels']['v'])
        tag = f'{tag}_{tag_extra}' if tag else tag_extra 
        super().__init__(body, design, tag=tag, rise=rise)

        design = design['flare-skirt']
        self.rise = design['rise']['v'] if rise is None else rise
        waist, hip_line, _ = self.eval_rise(self.rise)
        n_panels = design['skirt-many-panels']['n_panels']['v']

        # Length is dependent on length of legs
        length = hip_line + design['length']['v'] * body['_leg_length']

        # NOTE: with some combinations of rise and length parameters, length may become too small/negative
        # Hence putting a min positive value here
        length = max(length, min_len)

        flare_coeff_pi = 1 + design['suns']['v'] * length * 2 * np.pi / waist

        self.front = ThinSkirtPanel('front', 
                                    panel_w := waist / n_panels,
                                    bottom_width=panel_w * flare_coeff_pi,
                                    length=length,
                                    b_curvature=design['skirt-many-panels']['panel_curve']['v'])
        
        # Move far enough s.t. the widest part of the panels fit on the circle
        dist = self.front.interfaces['bottom'].edges.length() / (2 * np.tan(np.pi / n_panels))

        self.front.translate_to([-dist, body['_waist_level'], 0])
        # Align orientation with a body
        self.front.rotate_by(R.from_euler('XYZ', [0, -90, 0], degrees=True))
        self.front.rotate_align([-dist, 0, panel_w / 2])

        # Upd interface orientation
        self.front.interfaces['top'].reverse(True)

        # Create new panels
        self.subs = pyg.ops.distribute_Y(self.front, n_panels, name_tag='skirt_panel')

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces['left'],
                                         self.subs[i].interfaces['right']))
            
        self.stitching_rules.append((self.subs[-1].interfaces['left'],
                                     self.subs[0].interfaces['right']))

        # Define the interface
        self.interfaces = {
            'top': pyg.Interface.from_multiple(*[sub.interfaces['top']
                                                 for sub in self.subs])
        }
    
    def length(self):
        return self.front.length()

