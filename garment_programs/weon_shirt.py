from copy import deepcopy
from typing import Optional, Any

import numpy as np
import pygarment as pyg

from garment_programs.base_classes import BaseBodicePanel
from assets.garment_programs import collars
from garment_programs import weon_torso
from garment_programs import weon_sleeves
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.shirt_design import ShirtDesign


class BodiceFrontHalf(BaseBodicePanel):
    # Dart and fit constants
    BOTTOM_DART_WIDTH_FACTOR = 2 / 3
    SIDE_DART_DEPTH_FACTOR = 0.75
    BOTTOM_DART_DEPTH_FACTOR = 0.9

    def __init__(
        self,
        name: str,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Initialize half of a fitted bodice front panel.

        Parameters
        ----------
        name : str
            Name of the panel.
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """
        super().__init__(name, body, design)

        m_bust = body['bust']
        m_waist = body['waist']

        # sizes   
        bust_point = body['bust_points'] / 2
        front_frac = (body['bust'] - body['back_width']) / 2 / body['bust'] 

        self.width = front_frac * m_bust
        waist = (m_waist - body['waist_back_width']) / 2
        sh_tan = np.tan(np.deg2rad(body['_shoulder_incl']))
        shoulder_incl = sh_tan * self.width
        bottom_d_width = (self.width - waist) * self.BOTTOM_DART_WIDTH_FACTOR

        adjustment = sh_tan * (self.width - body['shoulder_w'] / 2)
        max_len = body['waist_over_bust_line'] - adjustment

        # side length is adjusted due to shoulder inclination
        # for the correct sleeve fitting
        fb_diff = (front_frac - (0.5 - front_frac)) * body['bust']
        back_adjustment = sh_tan * (body['back_width'] / 2 - body['shoulder_w'] / 2)
        side_len = body['waist_line'] - back_adjustment - sh_tan * fb_diff 

        self.edges.append(pyg.EdgeSeqFactory.from_verts(
            [0, 0], 
            [-self.width, 0],
            [-self.width, max_len], 
            [0, max_len + shoulder_incl]
        ))
        self.edges.close_loop()

        # Side dart
        bust_line = body['waist_line'] - body['_bust_line']
        side_d_depth = self.SIDE_DART_DEPTH_FACTOR * (self.width - bust_point)    # NOTE: calculated value 
        side_d_width = max_len - side_len
        s_edge, side_interface = self.add_dart(
            pyg.EdgeSeqFactory.dart_shape(side_d_width, side_d_depth),
            self.edges[1], 
            offset=bust_line + side_d_width / 2)
        self.edges.substitute(1, s_edge)

        # Take some fabric from the top to match the shoulder width
        s_edge[-1].end[0] += (x_upd:=self.width - body['shoulder_w'] / 2)
        s_edge[-1].end[1] += (sh_tan * x_upd)

        # Bottom dart
        b_edge, b_interface = self.add_dart(
            pyg.EdgeSeqFactory.dart_shape(bottom_d_width, self.BOTTOM_DART_DEPTH_FACTOR * bust_line),
            self.edges[0], 
            offset=bust_point + bottom_d_width / 2
        )
        self.edges.substitute(0, b_edge)
        # Take some fabric from side in the bottom (!: after side dart insertion)
        b_edge[-1].end[0] = - (waist + bottom_d_width) 

        # Interfaces
        self.interfaces = {
            'outside':  pyg.Interface(self, side_interface),   # side_interface,    # pyp.Interface(self, [side_interface]),  #, self.edges[-3]]),
            'inside': pyg.Interface(self, self.edges[-1]),
            'shoulder': pyg.Interface(self, self.edges[-2]),
            'bottom': pyg.Interface(self, b_interface),

            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyg.Interface(
                self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyg.Interface(
                self, [self.edges[-2], self.edges[-1]])
        }
  
        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - max_len - shoulder_incl, 0])


class BodiceBackHalf(BaseBodicePanel):
    """Panel for the back of a basic fitted bodice block."""

    # Dart and fit constants
    SIDE_ADJUSTMENT_THRESHOLD = 4
    SIDE_ADJUSTMENT_FACTOR = 1 / 6
    BOTTOM_DART_DEPTH_FACTOR = 1.0
    SMALL_DART_DEPTH_FACTOR = 0.9
    DART_POSITION_MULTIPLIER = 0.5

    def __init__(
        self,
        name: str,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Initialize the back panel of a basic fitted bodice block.

        Parameters
        ----------
        name : str
            Name of the panel.
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """
        super().__init__(name, body, design)

        # Overall measurements        
        self.width = body['back_width'] / 2
        waist = body['waist_back_width'] / 2  
        # NOTE: no inclination on the side, since there is not much to begin with
        waist_width = self.width if waist < self.width else waist  
        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['_shoulder_incl']))) * self.width

        # Adjust to make sure length is measured from the shoulder
        # and not the de-fact side of the garment
        back_adjustment = sh_tan * (self.width - body['shoulder_w'] / 2)
        length = body['waist_line'] - back_adjustment

        # Base edge loop
        edge_0 = pyg.CurveEdgeFactory.curve_from_tangents(
            start=[0, shoulder_incl / 4],  # back a little shorter 
            end=[-waist_width, 0],
            target_tan0=[-1, 0]
        )
        self.edges.append(edge_0)
        self.edges.append(pyg.EdgeSeqFactory.from_verts(
            edge_0.end,
            [-self.width, body['waist_line'] - body['_bust_line']],  # from the bottom
            [-self.width, length],   
            [0, length + shoulder_incl],   # Add some fabric for the neck (inclination of shoulders)
        ))
        self.edges.close_loop()
        
        # Take some fabric from the top to match the shoulder width
        self.interfaces = {
            'outside': pyg.Interface(
                self, [self.edges[1], self.edges[2]]),
            'inside': pyg.Interface(self, self.edges[-1]),
            'shoulder': pyg.Interface(self, self.edges[-2]),
            'bottom': pyg.Interface(self, self.edges[0]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyg.Interface(
                self, pyg.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyg.Interface(
                self, pyg.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        if waist < self.get_width(self.edges[2].end[1] - self.edges[2].start[1]):
            w_diff = waist_width - waist
            side_adj = 0 if w_diff < self.SIDE_ADJUSTMENT_THRESHOLD else w_diff * self.SIDE_ADJUSTMENT_FACTOR  # NOTE: don't take from sides if the difference is too small
            bottom_d_width = w_diff - side_adj
            bottom_d_width /= 2   # double darts
            bottom_d_depth = self.BOTTOM_DART_DEPTH_FACTOR * (length - body['_bust_line'])  # calculated value
            bottom_d_position = body['bum_points'] / 2

            # TODOLOW Avoid hardcoding for matching with the bottoms?
            dist = bottom_d_position * self.DART_POSITION_MULTIPLIER  # Dist between darts -> dist between centers
            b_edge, b_interface = self.add_dart(
                pyg.EdgeSeqFactory.dart_shape(bottom_d_width, self.SMALL_DART_DEPTH_FACTOR * bottom_d_depth),
                self.edges[0], 
                offset=bottom_d_position + dist / 2 + bottom_d_width + bottom_d_width / 2,
            )
            b_edge, b_interface = self.add_dart(
                pyg.EdgeSeqFactory.dart_shape(bottom_d_width, bottom_d_depth),
                b_edge[0], 
                offset=bottom_d_position - dist / 2 + bottom_d_width / 2,
                edge_seq=b_edge,
                int_edge_seq=b_interface,
            )

            self.edges.substitute(0, b_edge)
            self.interfaces['bottom'] = pyg.Interface(self, b_interface)

            # Remove fabric from the sides if the diff is big enough
            b_edge[-1].end[0] += side_adj

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length - shoulder_incl, 0])

    def get_width(self, level: float) -> float:
        """Get the width of the panel at a given level.
        
        Parameters:
        -----------
        level : float
            Vertical level from the top of the panel.
        
        Returns:
        --------
        float
            Width of the panel at the given level.
        """
        return self.width

class BodiceHalf(pyg.Component):
    """Definition of a half of an upper garment with sleeves and collars"""

    # Panel placement constants
    FRONT_TORSO_TRANSLATION_Z = 30
    BACK_TORSO_TRANSLATION_Z = -25

    # Sleeve placement constants
    SLEEVE_PLACEMENT_GAP_BASE = -1
    SLEEVE_PLACEMENT_GAP_FACTOR = 10

    def __init__(
        self,
        name: str,
        body: BodyDefinition | dict,
        design: dict,
        fitted: bool = True
    ) -> None:
        """Define half of an upper garment, including torso, sleeves, and collars.

        Parameters
        ----------
        name : str
            Name of the component (e.g., 'right' or 'left').
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        fitted : bool, optional
            If True, creates a fitted bodice; otherwise, a looser torso (tee-style).
            Default is True.
        """
        super().__init__(name)

        design = deepcopy(design)   # Recalculate freely!
        
        # Create ShirtDesign from the design dict and store it
        self.shirt_design = ShirtDesign(design)

        # Torso
        if fitted:
            self.ftorso = BodiceFrontHalf(f'{name}_ftorso', body, design).translate_by([0, 0, self.FRONT_TORSO_TRANSLATION_Z])
            self.btorso = BodiceBackHalf(f'{name}_btorso', body, design).translate_by([0, 0, self.BACK_TORSO_TRANSLATION_Z])
        else:
            self.ftorso = weon_torso.TorsoFrontHalfPanel(f'{name}_ftorso', body, design['shirt']).translate_by([0, 0, self.FRONT_TORSO_TRANSLATION_Z])
            self.btorso = weon_torso.TorsoBackHalfPanel(f'{name}_btorso', body, design['shirt']).translate_by([0, 0, self.BACK_TORSO_TRANSLATION_Z])

        # Interfaces
        self.interfaces.update({
            'f_bottom': self.ftorso.interfaces['bottom'],
            'b_bottom': self.btorso.interfaces['bottom'],
            'front_in': self.ftorso.interfaces['inside'],
            'back_in': self.btorso.interfaces['inside']
        })

        # Sleeves/collar cuts
        self.sleeve: Optional[weon_sleeves.Sleeve] = None
        self.collar_comp: Optional[Any] = None
        self.eval_dep_params(body, design)

        if self.shirt_design.shirt.strapless and fitted:  # NOTE: Strapless design only for fitted tops
            self.make_strapless(body, design)
        else:
            # Sleeves and collars 
            self.add_sleeves(name, body, design)
            self.add_collars(name, body, design)
            self.stitching_rules.append((
                self.ftorso.interfaces['shoulder'], 
                self.btorso.interfaces['shoulder']
            ))  # tops

        # Main connectivity
        self.stitching_rules.append((
            self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']))   # sides

    def eval_dep_params(
        self,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Evaluate dependent design parameters based on body measurements.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary (modified in place).
        """

        # Sleeves
        # NOTE assuming the vertical side is the first argument
        max_cwidth = self.ftorso.interfaces['shoulder_corner'].edges[0].length() - 1  # cm
        min_cwidth = self.shirt_design.shirt.scye_depth - self.shirt_design.shirt.shoulder_slant
        v = self.shirt_design.sleeve.connecting_width
        design['sleeve']['connecting_width']['v'] = min(min_cwidth + min_cwidth * v, max_cwidth)

        # Depth
        # Collar depth is given w.r.t. length.
        # adjust for the shoulder inclination
        tg = np.tan(np.deg2rad(body['_shoulder_incl']))
        max_f_len = self.ftorso.interfaces['collar_corner'].edges[1].length() - tg * self.ftorso.get_width(0) - 1  # cm
        max_b_len = self.btorso.interfaces['collar_corner'].edges[1].length() - tg * self.btorso.get_width(0) - 1  # cm

        design['collar']['f_strapless_depth'] = {}
        design['collar']['f_strapless_depth']['v'] = min(
            self.shirt_design.collar.fc_depth * body['_bust_line'], 
            max_f_len)
        

        design['collar']['b_strapless_depth'] = {}
        design['collar']['b_strapless_depth']['v'] =  min(
            self.shirt_design.collar.bc_depth * body['_bust_line'], 
            max_b_len)

    def add_sleeves(
        self,
        name: str,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Add sleeves to the bodice half.
        
        Parameters
        ----------
        name : str
            Name of the component (e.g., 'right' or 'left').
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """

        self.sleeve = weon_sleeves.Sleeve(
            name, body, design, 
            front_w=(self.shirt_design.shirt.width_chest - self.shirt_design.shirt.smallest_width) / 2,
            back_w=(self.shirt_design.shirt.width_chest - self.shirt_design.shirt.back_width) / 2,
            front_hole_edge=self.ftorso.edges[-3],
            back_hole_edge=self.btorso.edges[-3],
        )

        _, f_sleeve_int = pyg.ops.cut_corner(
            self.sleeve.interfaces['in_front_shape'].edges, 
            self.ftorso.interfaces['shoulder_corner'], 
            verbose=self.verbose
        )
        _, b_sleeve_int = pyg.ops.cut_corner(
            self.sleeve.interfaces['in_back_shape'].edges, 
            self.btorso.interfaces['shoulder_corner'],
            verbose=self.verbose
        )

        if not self.shirt_design.sleeve.sleeveless:
            # Ordering
            bodice_sleeve_int = pyg.Interface.from_multiple(
                f_sleeve_int.reverse(with_edge_dir_reverse=True),
                b_sleeve_int.reverse(),
            )    
            self.stitching_rules.append((
                self.sleeve.interfaces['in'], 
                bodice_sleeve_int
            ))

            # NOTE: This is a heuristic tuned for arm poses 30 deg-60 deg 
            # used in the dataset
            # FIXME Needs a better general solution
            gap = self.SLEEVE_PLACEMENT_GAP_BASE - body['arm_pose_angle'] / self.SLEEVE_PLACEMENT_GAP_FACTOR
            self.sleeve.place_by_interface(
                self.sleeve.interfaces['in'], 
                bodice_sleeve_int, 
                gap=gap,   
                alignment='top',
            )

        # Add edge labels
        f_sleeve_int.edges.propagate_label(f'{self.name}_armhole')
        b_sleeve_int.edges.propagate_label(f'{self.name}_armhole')
    
    def add_collars(
        self,
        name: str,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Add collars to the bodice half.
        
        Parameters
        ----------
        name : str
            Name of the component (e.g., 'right' or 'left').
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """

        # Front
        collar_type = getattr(
            collars, 
            str(self.shirt_design.collar.component.style), 
            collars.NoPanelsCollar
            )
        
        self.collar_comp = collar_type(name, body, design)
        
        # Project shape
        _, fc_interface = pyg.ops.cut_corner(
            self.collar_comp.interfaces['front_proj'].edges, 
            self.ftorso.interfaces['collar_corner'],
            verbose=self.verbose
        )
        _, bc_interface = pyg.ops.cut_corner(
            self.collar_comp.interfaces['back_proj'].edges, 
            self.btorso.interfaces['collar_corner'],
            verbose=self.verbose
        )

        # Add stitches/interfaces
        if 'bottom' in self.collar_comp.interfaces:
            self.stitching_rules.append((
                pyg.Interface.from_multiple(fc_interface, bc_interface), 
                self.collar_comp.interfaces['bottom']
            ))

        # Upd front interfaces accordingly
        if 'front' in self.collar_comp.interfaces:
            self.interfaces['front_collar'] = self.collar_comp.interfaces['front']
            self.interfaces['front_in'] = pyg.Interface.from_multiple(
                self.ftorso.interfaces['inside'], self.interfaces['front_collar']
            )
        if 'back' in self.collar_comp.interfaces:
            self.interfaces['back_collar'] = self.collar_comp.interfaces['back']
            self.interfaces['back_in'] = pyg.Interface.from_multiple(
                self.btorso.interfaces['inside'], self.interfaces['back_collar']
            )
        
        # Add edge labels
        fc_interface.edges.propagate_label(f'{self.name}_collar')
        bc_interface.edges.propagate_label(f'{self.name}_collar')

    def make_strapless(
        self,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Modify the bodice half to be strapless.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """

        out_depth = design['sleeve']['connecting_width']['v']  # May have been modified in eval_dep_params
        f_in_depth = design['collar']['f_strapless_depth']['v']  # May have been modified in eval_dep_params
        b_in_depth = design['collar']['b_strapless_depth']['v']  # May have been modified in eval_dep_params

        # Shoulder adjustment for the back
        # TODOLOW Shoulder adj evaluation should be a function
        shoulder_angle = np.deg2rad(body['_shoulder_incl'])
        sleeve_balance = body['_base_sleeve_balance'] / 2
        back_w = self.btorso.get_width(0)
        shoulder_adj = np.tan(shoulder_angle) * (back_w - sleeve_balance)
        out_depth -= shoulder_adj

        # Upd back
        self._adjust_top_level(self.btorso, out_depth, b_in_depth)

        # Front depth determined by ~compensating for lenght difference
        len_back = self.btorso.interfaces['outside'].edges.length()
        len_front = self.ftorso.interfaces['outside'].edges.length()
        self._adjust_top_level(self.ftorso, out_depth, f_in_depth, target_remove=(len_front - len_back))
        
        # Placement
        # NOTE: The commented line places the top a bit higher, increasing the chanced of correct drape
        # Surcumvented by attachment constraint, so removed for nicer alignment in asymmetric garments
        # self.translate_by([0, out_depth - body['_armscye_depth'] * 0.75, 0])   # adjust for better localisation

        # Add a label
        self.ftorso.interfaces['shoulder'].edges.propagate_label('strapless_top')
        self.btorso.interfaces['shoulder'].edges.propagate_label('strapless_top')


    def _adjust_top_level(
        self,
        panel: BaseBodicePanel,
        out_level: float,
        in_level: float,
        target_remove: Optional[float] = None
    ) -> None:
        """Crop the top of the bodice front/back panel for strapless style.
        
        Parameters
        ----------
        panel : BaseBodicePanel
            The panel to adjust.
        out_level : float
            Outer depth to remove.
        in_level : float
            Inner depth to remove.
        target_remove : float, optional
            If set, determines the length difference that should be compensated
            after cutting the depth.
        """
        # TODOLOW Should this be the panel's function?

        panel_top = panel.interfaces['shoulder'].edges[0]
        min_y = min(panel_top.start[1], panel_top.end[1])  

        # Order vertices
        ins, out = panel_top.start, panel_top.end
        if panel_top.start[1] < panel_top.end[1]:
            ins, out = out, ins
    
        # Inside is a simple vertical line and can be adjusted by chaning Y value
        ins[1] = min_y - in_level

        # Outside could be inclined, so needs further calculations
        outside_edge = panel.interfaces['outside'].edges[-1]
        bot, top = outside_edge.start, outside_edge.end
        if bot is out:
            bot, top = top, bot
        
        if target_remove is not None:
            # Adjust the depth to remove this length exactly
            angle_sin = abs(out[1] - bot[1]) / outside_edge.length()   
            curr_remove = out_level / angle_sin
            length_diff = target_remove - curr_remove
            adjustment = length_diff * angle_sin
            out_level += adjustment
        
        angle_cotan = abs(out[0] - bot[0]) / abs(out[1] - bot[1])
        out[0] -= out_level * angle_cotan  
        out[1] = min_y - out_level


    def length(self) -> float:
        """Return the length of the bodice half.
        
        Returns:
        --------
        float
            Length of the bodice half.
        """
        return self.btorso.length()


class Shirt(pyg.Component):
    """Panel for the front of upper garments with darts to properly fit it to
    the shape"""

    def __init__(
        self,
        body: BodyDefinition | dict,
        design: dict,
        fitted: bool = False
    ) -> None:
        """Create a shirt garment component.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        fitted : bool, optional
            If True, creates a fitted shirt; otherwise, a looser fit.
            Default is False.
        """
        name_with_params = f"{self.__class__.__name__}"
        super().__init__(name_with_params)

        # Create ShirtDesign from the design dict and store it
        self.shirt_design = ShirtDesign(design)
        
        design = self.eval_dep_params(design)

        self.right = BodiceHalf(f'right', body, design, fitted=fitted)
        self.left = BodiceHalf(
            f'left', body, 
            design['left'] if self.shirt_design.left.enable_asym else design, 
            fitted=fitted).mirror()

        self.stitching_rules.append((self.right.interfaces['front_in'],
                                     self.left.interfaces['front_in']))
        self.stitching_rules.append((self.right.interfaces['back_in'],
                                     self.left.interfaces['back_in']))

        # Adjust interface ordering for correct connectivity
        self.interfaces = {   # Bottom connection
            'bottom': pyg.Interface.from_multiple(
                self.right.interfaces['f_bottom'].reverse(),
                self.left.interfaces['f_bottom'],
                self.left.interfaces['b_bottom'].reverse(),
                self.right.interfaces['b_bottom'],)
        }

    def eval_dep_params(self, design: dict) -> dict:
        """Evaluate dependent design parameters based on body measurements.
        
        Parameters
        ----------
        design : dict
            Design parameters dictionary.
        
        Returns
        -------
        dict
            Updated design parameters dictionary.
        """

        # NOTE: Support for full collars with partially strapless top
        # or combination of paneled collar styles
        # requres further development
        # TODOLOW enable this one to work
        if self.shirt_design.left.enable_asym:
            # Force no collars since they are not compatible with each other
            design = deepcopy(design)
            design['collar']['component']['style']['v'] = None
            design['left']['collar']['component'] = dict(style=dict(v=None))
            
            # Left-right design compatibility 
            design['left']['shirt'].update(length={})
            design['left']['shirt']['length']['v'] = self.shirt_design.shirt.length
            
            design['left']['collar'].update(fc_depth={}, bc_depth={})
            design['left']['collar']['fc_depth']['v'] = self.shirt_design.collar.fc_depth
            design['left']['collar']['bc_depth']['v'] = self.shirt_design.collar.bc_depth

        return design

    def length(self) -> float:
        """Return the length of the shirt.
        
        Returns:
        --------
        float
            Length of the shirt.
        """
        return self.right.length()

class FittedShirt(Shirt):
    """Creates fitted shirt.
    
    NOTE: Separate class is used for selection convenience.
    Even though most of the processing is the same (hence implemented with
    the same components except for panels), design parametrization differs
    significantly. With that, we decided to separate the top level names.
    """
    
    def __init__(
        self,
        body: BodyDefinition | dict,
        design: dict
    ) -> None:
        """Initialize a fitted shirt.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """
        super().__init__(body, design, fitted=True)
