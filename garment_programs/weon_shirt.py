from typing import Optional, Any, List

import numpy as np
import pygarment as pyg
from scipy.spatial.transform import Rotation as R

from garment_programs.base_classes import BaseBodicePanel
from garment_programs.garment_program_utils import AttachmentHandler
from garment_programs.weon_torso import TorsoFrontHalfPanel, TorsoBackHalfPanel
from garment_programs import weon_sleeves
from garment_programs.garment_enums import InterfaceName, EdgeLabel
from pattern_definitions.body_definition import BodyDefinition
from garment_programs.weon_collars import NoPanelsCollar

from pattern_definitions.shirt_design import ShirtDesign
from pattern_definitions.torso_design import TorsoDesign
from config import AttachmentConstraint


class BodiceFrontHalf(BaseBodicePanel):
    # Dart and fit constants
    BOTTOM_DART_WIDTH_FACTOR: float = 2 / 3
    SIDE_DART_DEPTH_FACTOR: float = 0.75
    BOTTOM_DART_DEPTH_FACTOR: float = 0.9
    
    # Class attributes
    width: float

    def __init__(
        self,
        name: str,
        body: BodyDefinition | dict,
        torso_design: TorsoDesign
    ) -> None:
        """Initialize half of a fitted bodice front panel.

        Parameters
        ----------
        name : str
            Name of the panel.
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        torso_design : TorsoDesign
            Design parameters dictionary.
        """
        super().__init__(name, torso_design)

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
            InterfaceName.OUTSIDE:  pyg.Interface(self, side_interface),   # side_interface,    # pyp.Interface(self, [side_interface]),  #, self.edges[-3]]),
            InterfaceName.INSIDE: pyg.Interface(self, self.edges[-1]),
            InterfaceName.SHOULDER: pyg.Interface(self, self.edges[-2]),
            InterfaceName.BOTTOM: pyg.Interface(self, b_interface),

            # Reference to the corner for sleeve and collar projections
            InterfaceName.SHOULDER_CORNER: pyg.Interface(
                self, [self.edges[-3], self.edges[-2]]),
            InterfaceName.COLLAR_CORNER: pyg.Interface(
                self, [self.edges[-2], self.edges[-1]])
        }
  
        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - max_len - shoulder_incl, 0])


class BodiceBackHalf(BaseBodicePanel):
    """Panel for the back of a basic fitted bodice block."""

    # Dart and fit constants
    SIDE_ADJUSTMENT_THRESHOLD: int = 4
    SIDE_ADJUSTMENT_FACTOR: float = 1 / 6
    BOTTOM_DART_DEPTH_FACTOR: float = 1.0
    SMALL_DART_DEPTH_FACTOR: float = 0.9
    DART_POSITION_MULTIPLIER: float = 0.5
    
    # Class attributes
    width: float

    def __init__(
        self,
        name: str,
        body: BodyDefinition | dict,
        torso_design: TorsoDesign
    ) -> None:
        """Initialize the back panel of a basic fitted bodice block.

        Parameters
        ----------
        name : str
            Name of the panel.
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        torso_design : TorsoDesign
            Design parameters dictionary.
        """
        super().__init__(name, torso_design)

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
            InterfaceName.OUTSIDE: pyg.Interface(
                self, [self.edges[1], self.edges[2]]),
            InterfaceName.INSIDE: pyg.Interface(self, self.edges[-1]),
            InterfaceName.SHOULDER: pyg.Interface(self, self.edges[-2]),
            InterfaceName.BOTTOM: pyg.Interface(self, self.edges[0]),
            # Reference to the corners for sleeve and collar projections
            InterfaceName.SHOULDER_CORNER: pyg.Interface(
                self, pyg.EdgeSequence(self.edges[-3], self.edges[-2])),
            InterfaceName.COLLAR_CORNER: pyg.Interface(
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
            self.interfaces[InterfaceName.BOTTOM] = pyg.Interface(self, b_interface)

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
    FRONT_TORSO_TRANSLATION_Z: int = 30
    BACK_TORSO_TRANSLATION_Z: int = -25

    # Sleeve placement constants
    SLEEVE_PLACEMENT_GAP_BASE: int = -1
    SLEEVE_PLACEMENT_GAP_FACTOR: int = 10

    # Class attributes
    shirt_design: ShirtDesign
    ftorso: TorsoFrontHalfPanel
    btorso: TorsoBackHalfPanel
    sleeve: Optional[weon_sleeves.Sleeve]
    collar_comp: Optional[Any]
    _bodice_sleeve_int: Optional[pyg.EdgeSequence]
    _sleeve_placement_gap: Optional[float]

    def __init__(
        self,
        name: str,
        shirt_design: ShirtDesign,
        arm_pose_angle: float,
        fitted: bool = True
    ) -> None:
        """Define half of an upper garment, including torso, sleeves, and collars.

        Parameters
        ----------
        name : str
            Name of the component (e.g., 'right' or 'left').
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        shirt_design : ShirtDesign
            Shirt design object.
        arm_pose_angle : float
            Arm pose angle.
        fitted : bool, optional
            If True, creates a fitted bodice; otherwise, a looser torso (tee-style).
            Default is True.
        """
        super().__init__(name)

        # Create ShirtDesign from the design dict and store it
        self.shirt_design = shirt_design

        # Torso
        if fitted:
            raise NotImplementedError("Fitted bodice not implemented yet.")
        else:
            self.ftorso = TorsoFrontHalfPanel(name=f'{name}_ftorso', shirt_design=shirt_design)
            self.ftorso.translate_by([0, 0, self.FRONT_TORSO_TRANSLATION_Z])

            self.btorso = TorsoBackHalfPanel(name=f'{name}_btorso', shirt_design=shirt_design)
            self.btorso.translate_by([0, 0, self.BACK_TORSO_TRANSLATION_Z])

        # Interfaces
        self.interfaces.update({
            InterfaceName.F_BOTTOM: self.ftorso.interfaces[InterfaceName.BOTTOM],
            InterfaceName.B_BOTTOM: self.btorso.interfaces[InterfaceName.BOTTOM],
            InterfaceName.FRONT_IN: self.ftorso.interfaces[InterfaceName.INSIDE],
            InterfaceName.BACK_IN: self.btorso.interfaces[InterfaceName.INSIDE]
        })

        # Sleeves/collar cuts
        self.sleeve: Optional[weon_sleeves.Sleeve] = None
        self.collar_comp: Optional[Any] = None
        self._bodice_sleeve_int: Optional[pyg.EdgeSequence] = None
        self._sleeve_placement_gap: Optional[float] = None

        if self.shirt_design.torso_design.strapless and fitted:  # NOTE: Strapless design only for fitted tops
            #self.make_strapless(body, design)
            raise NotImplementedError("Strapless design not implemented yet.")
        else:
            # Sleeves and collars 
            # NOTE assuming the vertical side is the first argument
            max_cwidth = self.ftorso.interfaces[InterfaceName.SHOULDER_CORNER].edges[0].length() - 1  # cm
            min_cwidth = self.shirt_design.torso_design.scye_depth - self.shirt_design.torso_design.shoulder_slant
            adjusted_connecting_width = min(min_cwidth + min_cwidth * self.shirt_design.sleeve_design.connecting_width, max_cwidth)
            self.add_sleeves(name, arm_pose_angle, adjusted_connecting_width)

            self.add_collars(name)
            self.stitching_rules.append((
                self.ftorso.interfaces[InterfaceName.SHOULDER], 
                self.btorso.interfaces[InterfaceName.SHOULDER]
            ))  # tops

        # Main connectivity
        self.stitching_rules.append((
            self.ftorso.interfaces[InterfaceName.OUTSIDE], self.btorso.interfaces[InterfaceName.OUTSIDE]))   # sides

    def add_sleeves(
        self,
        name: str,
        arm_pose_angle: float,
        connecting_width: float
    ) -> None:
        """Add sleeves to the bodice half.
        
        Parameters
        ----------
        name : str
            Name of the component (e.g., 'right' or 'left').
        design : dict
            Design parameters dictionary.
        arm_pose_angle : float
            Arm pose angle.
        connecting_width: float
            Connecting width of the sleeves.
        """

        self.sleeve = weon_sleeves.Sleeve(
            tag=name,
            shirt_design=self.shirt_design.torso_design,
            sleeve_design=self.shirt_design.sleeve_design,
            front_w=(self.shirt_design.torso_design.width_chest - self.shirt_design.torso_design.smallest_width) / 2,
            back_w=(self.shirt_design.torso_design.width_chest - self.shirt_design.torso_design.back_width) / 2,
            front_hole_edge=self.ftorso.edges[-3],
            back_hole_edge=self.btorso.edges[-3],
            adjusted_connecting_width=connecting_width,
        )

        _, f_sleeve_int = pyg.ops.cut_corner(
            self.sleeve.interfaces[InterfaceName.IN_FRONT_SHAPE].edges, 
            self.ftorso.interfaces[InterfaceName.SHOULDER_CORNER], 
            verbose=self.verbose
        )
        _, b_sleeve_int = pyg.ops.cut_corner(
            self.sleeve.interfaces[InterfaceName.IN_BACK_SHAPE].edges, 
            self.btorso.interfaces[InterfaceName.SHOULDER_CORNER],
            verbose=self.verbose
        )

        if not self.shirt_design.sleeve_design.sleeveless:
            # Ordering
            bodice_sleeve_int = pyg.Interface.from_multiple(
                f_sleeve_int.reverse(with_edge_dir_reverse=True),
                b_sleeve_int.reverse(),
            )    
            self.stitching_rules.append((
                self.sleeve.interfaces[InterfaceName.IN], 
                bodice_sleeve_int
            ))

            # NOTE: This is a heuristic tuned for arm poses 30 deg-60 deg 
            # used in the dataset
            # FIXME Needs a better general solution
            gap = self.SLEEVE_PLACEMENT_GAP_BASE - arm_pose_angle / self.SLEEVE_PLACEMENT_GAP_FACTOR
            self.sleeve.place_by_interface(
                self.sleeve.interfaces[InterfaceName.IN], 
                bodice_sleeve_int, 
                gap=gap,   
                alignment='top',
            )
            
            # Store armhole interface and gap for re-alignment after rotation
            self._bodice_sleeve_int = bodice_sleeve_int
            self._sleeve_placement_gap = gap

        # Add edge labels
        f_sleeve_int.edges.propagate_label(f'{self.name}_{EdgeLabel.ARMHOLE}')
        b_sleeve_int.edges.propagate_label(f'{self.name}_{EdgeLabel.ARMHOLE}')
    
    def translate_and_rotate_sleeve(self, translation: tuple[float, float, float], angle: float) -> None:
        """Translate and rotate the sleeve piece, then re-align with armhole.
        
        Parameters
        ----------
        translation : tuple[float, float, float]
            Translation to apply to the sleeve piece.
        angle : float
            Angle to rotate the sleeve piece.
        """
        if self.sleeve is not None:
            self.sleeve.translate_by(translation)
            self.sleeve.rotate_by(R.from_euler(
                'XYZ', [0, 0, angle], degrees=True))
            
            # Re-align sleeve with armhole after rotation to maintain proper connection
            if self._bodice_sleeve_int is not None and not self.shirt_design.sleeve_design.sleeveless:
                self.sleeve.place_by_interface(
                    self.sleeve.interfaces[InterfaceName.IN], 
                    self._bodice_sleeve_int, 
                    gap=self._sleeve_placement_gap,   
                    alignment='top',
                ) 

    def add_collars(
        self,
        name: str,
    ) -> None:
        """Add collars to the bodice half.
        
        Parameters
        ----------
        name : str
            Name of the component (e.g., 'right' or 'left').
        """

        # Front
        self.collar_comp = NoPanelsCollar(name, self.shirt_design.collar_design)
        
        # Project shape
        _, fc_interface = pyg.ops.cut_corner(
            self.collar_comp.interfaces[InterfaceName.FRONT_PROJ].edges, 
            self.ftorso.interfaces[InterfaceName.COLLAR_CORNER],
            verbose=self.verbose
        )
        _, bc_interface = pyg.ops.cut_corner(
            self.collar_comp.interfaces[InterfaceName.BACK_PROJ].edges, 
            self.btorso.interfaces[InterfaceName.COLLAR_CORNER],
            verbose=self.verbose
        )

        # Add stitches/interfaces
        if InterfaceName.BOTTOM in self.collar_comp.interfaces:
            self.stitching_rules.append((
                pyg.Interface.from_multiple(fc_interface, bc_interface), 
                self.collar_comp.interfaces[InterfaceName.BOTTOM]
            ))

        # Upd front interfaces accordingly
        if InterfaceName.FRONT in self.collar_comp.interfaces:
            self.interfaces[InterfaceName.FRONT_COLLAR] = self.collar_comp.interfaces[InterfaceName.FRONT]
            self.interfaces[InterfaceName.FRONT_IN] = pyg.Interface.from_multiple(
                self.ftorso.interfaces[InterfaceName.INSIDE], self.interfaces[InterfaceName.FRONT_COLLAR]
            )
        if InterfaceName.BACK in self.collar_comp.interfaces:
            self.interfaces[InterfaceName.BACK_COLLAR] = self.collar_comp.interfaces[InterfaceName.BACK]
            self.interfaces[InterfaceName.BACK_IN] = pyg.Interface.from_multiple(
                self.btorso.interfaces[InterfaceName.INSIDE], self.interfaces[InterfaceName.BACK_COLLAR]
            )
        
        # Add edge labels
        fc_interface.edges.propagate_label(f'{self.name}_{EdgeLabel.COLLAR}')
        bc_interface.edges.propagate_label(f'{self.name}_{EdgeLabel.COLLAR}')

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
        len_back = self.btorso.interfaces[InterfaceName.OUTSIDE].edges.length()
        len_front = self.ftorso.interfaces[InterfaceName.OUTSIDE].edges.length()
        self._adjust_top_level(self.ftorso, out_depth, f_in_depth, target_remove=(len_front - len_back))
        
        # Placement
        # NOTE: The commented line places the top a bit higher, increasing the chanced of correct drape
        # Surcumvented by attachment constraint, so removed for nicer alignment in asymmetric garments
        # self.translate_by([0, out_depth - body['_armscye_depth'] * 0.75, 0])   # adjust for better localisation

        # Add a label
        self.ftorso.interfaces[InterfaceName.SHOULDER].edges.propagate_label(EdgeLabel.STRAPLESS_TOP)
        self.btorso.interfaces[InterfaceName.SHOULDER].edges.propagate_label(EdgeLabel.STRAPLESS_TOP)


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

        panel_top = panel.interfaces[InterfaceName.SHOULDER].edges[0]
        min_y = min(panel_top.start[1], panel_top.end[1])  

        # Order vertices
        ins, out = panel_top.start, panel_top.end
        if panel_top.start[1] < panel_top.end[1]:
            ins, out = out, ins
    
        # Inside is a simple vertical line and can be adjusted by chaning Y value
        ins[1] = min_y - in_level

        # Outside could be inclined, so needs further calculations
        outside_edge = panel.interfaces[InterfaceName.OUTSIDE].edges[-1]
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

    # Class constants
    FRONT_TORSO_TRANSLATION_Z: int = 30
    
    # Class attributes
    shirt_design: ShirtDesign
    right: BodiceHalf
    left: BodiceHalf

    def __init__(
        self,
        shirt_design: ShirtDesign,
        arm_pose_angle: float,
        fitted: bool = False
    ) -> None:
        """Create a shirt garment component.
        
        Parameters
        ----------
        shirt_design : ShirtDesign
            Shirt design object.
        arm_pose_angle : float
            Arm pose angle, only used for bosy-sleeve init aligment.
        fitted : bool, optional
            If True, creates a fitted shirt; otherwise, a looser fit.
            Default is False.
        """

        name_with_params = f"{self.__class__.__name__}"
        super().__init__(name_with_params)

        # Create ShirtDesign from the design dict and store it
        self.shirt_design = shirt_design
        
        self.right = BodiceHalf('right',
                                self.shirt_design,
                                arm_pose_angle=arm_pose_angle,
                                fitted=fitted
                                )
        self.left = BodiceHalf('left',
                               self.shirt_design,
                               arm_pose_angle=arm_pose_angle,
                               fitted=fitted).mirror()

        self.stitching_rules.append((self.right.interfaces[InterfaceName.FRONT_IN],
                                     self.left.interfaces[InterfaceName.FRONT_IN]))
        self.stitching_rules.append((self.right.interfaces[InterfaceName.BACK_IN],
                                     self.left.interfaces[InterfaceName.BACK_IN]))

        # Adjust interface ordering for correct connectivity
        self.interfaces = {   # Bottom connection
            InterfaceName.BOTTOM: pyg.Interface.from_multiple(
                self.right.interfaces[InterfaceName.F_BOTTOM].reverse(),
                self.left.interfaces[InterfaceName.F_BOTTOM],
                self.left.interfaces[InterfaceName.B_BOTTOM].reverse(),
                self.right.interfaces[InterfaceName.B_BOTTOM],)
        }

    def length(self) -> float:
        """Return the length of the shirt.
        
        Returns:
        --------
        float
            Length of the shirt.
        """
        return self.right.length()
    
    @staticmethod
    def get_attachment_constraints() -> List[AttachmentConstraint]:
        """Get the list of attachment constraints for this shirt garment.
        
        Returns the attachment constraints required for simulating this shirt garment.
        Shirts do not require any attachment constraints by default.
        
        Returns:
        --------
        List[AttachmentConstraint]
            An empty list (shirts do not require attachment constraints).
        """
        return []
    
    def get_vertex_processor_callback(self):
        """Get the vertex processor callback for shirt attachment constraints.
        
        Shirts do not require custom vertex processing, so this returns a default
        callback that uses generic constraint processing.
        
        Returns:
        --------
        Callable[[BoxMesh], None] | None
            A callback that handles constraints with default behavior.
        """
        return AttachmentHandler.create_default_vertex_processor(Shirt)
    
    def apply_body_alignment(self, body: BodyDefinition) -> None:
        """Apply body alignment to the shirt.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        """
        # Apply sleeve rotations
        angle = body.arm_pose_angle

        self.right.translate_and_rotate_sleeve(translation=(0, 0, 0), angle=angle)
        
        # Apply to left sleeve (angle negated because left side is mirrored)
        self.left.translate_and_rotate_sleeve(translation=(0, 0, 0), angle=-angle)
        
        # Position entire shirt relative to body height (torso panels are positioned at Y=0,
        # but should be at body.height - body.head_l to align with body)
        self.translate_by([0, body.height - body.head_l, 0])


class FittedShirt(Shirt):
    """Creates fitted shirt.
    
    NOTE: Separate class is used for selection convenience.
    Even though most of the processing is the same (hence implemented with
    the same components except for panels), design parametrization differs
    significantly. With that, we decided to separate the top level names.
    """
    
    def __init__(
        self,
        shirt_design: ShirtDesign,
        arm_pose_angle: float,
    ) -> None:
        """Initialize a fitted shirt.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        """
        super().__init__(shirt_design, arm_pose_angle, fitted=True)
