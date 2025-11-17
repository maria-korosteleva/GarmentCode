
import numpy as np

import pygarment as pyg
from garment_programs.base_classes import BaseBottoms
from pattern_definitions.pants_design import PantsDesign
from pattern_definitions.body_definition import BodyDefinition


class PantPanel(pyg.Panel):
    """A pant panel component with optional dart fitting.
    
    This panel represents one half of a pants leg (front or back) and can be
    fitted with single or double darts at the waistline. The panel includes
    interfaces for connecting to other panels (outside seam, inside seam,
    crotch, top waistline, and bottom hem).
    
    Attributes:
    -----------
    DART_DEPTH_MULTIPLIER : float
        Multiplier for calculating dart depth based on waist-to-hip length.
    SMALL_DART_DEPTH_RATIO : float
        Ratio for smaller dart depth when using double darts.
    DART_POSITION_MULTIPLIER : float
        Multiplier for positioning double darts relative to single dart position.
    DART_OFFSET_MULTIPLIER_QUARTER : float
        Quarter-width offset multiplier for dart positioning.
    GRAINLINE_OFFSET_RATIO : float
        Ratio for positioning the grainline along the crotch extension.
    """
    
    # Dart and fit constants
    DART_DEPTH_MULTIPLIER: float = 0.8
    SMALL_DART_DEPTH_RATIO: float = 0.9
    DART_POSITION_MULTIPLIER: float = 0.5
    DART_OFFSET_MULTIPLIER_QUARTER: float = 0.25
    GRAINLINE_OFFSET_RATIO: float = 0.5
    
    def __init__(
            self,
            name: str,
            design: PantsDesign,
            rise: float,
            mid_rise: float,
            waist: float,
            hips: float,
            crotch_extension: float,
            hips_crotch_diff: float,
            crotch_hip_diff: float,
            dart_position: float,
            match_top_int_to: float | None = None,
            hipline_ext: float = 1,
            double_dart: bool = False,
            translation: np.ndarray = np.zeros(3)) -> None:
        """Initialize a pant panel with optional dart fitting.
        
        Creates a pant panel with curved edges for the outside seam, inside seam,
        crotch, and waistline. The panel can be fitted with darts at the waistline
        to accommodate the difference between waist and hip measurements.

        Parameters:
        -----------
        name : str
            Name identifier for this panel.
        design : PantsDesign
            Pants design parameters object containing measurements for widths and
            lengths (e.g., width_thigh, width_knee, width_calf, width_ankle, length_thigh_to_knee, length_knee_to_calf, length_calf_to_ankle,
            length_waist_to_hip).
        rise : float
            Total rise measurement from crotch to waist for this panel.
        mid_rise : float
            Average rise between front and back panels, used for alignment.
        waist : float
            Half-waist measurement (one side of the body).
        hips : float
            Half-hip measurement (one side of the body).
        crotch_extension : float
            Additional extension at the crotch point for fit and ease.
        hips_crotch_diff : float
            Vertical difference between the hips line and crotch point along the rise.
        crotch_hip_diff : float
            Vertical difference between the crotch point and hips line along the rise.
        dart_position : float
            Horizontal position of the dart(s) from the center front/back edge,
            measured along the waistline.
        match_top_int_to : float | None, optional
            If provided, the top interface will have a ruffle factor to match
            this target measurement. Used for correct balance line matching when
            connecting panels. Default is None.
        hipline_ext : float, optional
            Multiplier to extend the hipline for better fit adjustment.
            Default is 1.0.
        double_dart : bool, optional
            If True, creates two darts instead of one at the waistline.
            Default is False.
        translation : np.ndarray, optional
            3D translation vector for positioning the panel in space.
            Default is [0, 0, 0].

        Notes:
        ------
        The panel creates interfaces for:
        - 'outside': The outer side seam (right side for right leg)
        - 'inside': The inner leg seam
        - 'crotch': The crotch seam connecting front and back panels
        - 'top': The waistline interface (with optional darts)
        - 'bottom': The hem interface
        """

        super().__init__(name)

        dart_depth = design.length_waist_to_hip * hipline_ext * self.DART_DEPTH_MULTIPLIER
        dart_width = (hips - waist) / 2

        # --- Edges definition ---
        # Right
        total_length = design.length_thigh_to_knee + design.length_knee_to_calf + design.length_calf_to_ankle
        right_5 = pyg.CurveEdgeFactory.curve_from_tangents(
            start=[-hips, hips_crotch_diff + total_length],
            end=[-waist, mid_rise + total_length],
            target_tan0=np.array([0, 1]),
        )
        ext_point_thigh = right_5.evaluate_at_length(-hips_crotch_diff)

        right_4 = pyg.CurveEdgeFactory.curve_from_tangents(
            start=ext_point_thigh,
            end=right_5.start,
            target_tan1=np.array([0, 1]),
        )

        x_grainline = ext_point_thigh[0] + (design.width_thigh + crotch_extension) * self.GRAINLINE_OFFSET_RATIO

        right_3 = pyg.CurveEdgeFactory.interpolate_with_tangents(
            start=[x_grainline - design.width_knee / 2, (design.length_knee_to_calf + design.length_calf_to_ankle)],
            end=right_4.start,
            target_tan1=[right_4.as_curve().unit_tangent(0.0).real, right_4.as_curve().unit_tangent(0.0).imag],
            pre_start=[x_grainline - design.width_calf / 2, design.length_calf_to_ankle],
            initial_guess=[0.1, 0]
        )

        right_2 = pyg.CurveEdgeFactory.interpolate_with_tangents(
            start=[x_grainline - design.width_calf / 2, design.length_calf_to_ankle],
            end=right_3.start,
            pre_start=[x_grainline - design.width_ankle / 2, 0],
            post_end=right_3.end,
            initial_guess=[0.5, 0]
        )

        right_1 = pyg.CurveEdgeFactory.interpolate_with_tangents(
            start=[x_grainline - design.width_ankle / 2, 0],
            end=right_2.start,
            post_end=right_2.end,
            initial_guess=[0.5, 0]
        )
       
        top = pyg.Edge(
            start=right_5.end, 
            end=[0, (rise + total_length)], 
        )

        crotch_top = pyg.Edge(
            start=top.end,
            end=[0, crotch_hip_diff + total_length],
        )
        crotch_bottom = pyg.CurveEdgeFactory.curve_from_tangents(
            start=crotch_top.end,
            end=[ext_point_thigh[0] + hips + crotch_extension, total_length], 
            target_tan0=np.array([0, -1]),
            target_tan1=np.array([1, 0]),
            initial_guess=[0.5, -0.5] 
        )

        left_top = pyg.CurveEdgeFactory.interpolate_with_tangents(
            start=crotch_bottom.end,
            end=[right_2.end[0] + design.width_knee, design.length_knee_to_calf + design.length_calf_to_ankle], 
            post_end=[x_grainline + design.width_calf / 2, design.length_calf_to_ankle],
            initial_guess=[0.3, 0]
        )

        left_middle = pyg.CurveEdgeFactory.interpolate_with_tangents(
            start=left_top.end,
            end=[x_grainline + design.width_calf / 2, design.length_calf_to_ankle],
            post_end=[x_grainline + design.width_ankle / 2, 0],
            initial_guess=[0.5, 0]
        )

        left_bottom = pyg.CurveEdgeFactory.interpolate_with_tangents(
            start=left_middle.end,
            end=[x_grainline + design.width_ankle / 2, 0],
            pre_start=left_middle.start,
            initial_guess=[0.5, 0]
        )
        self.edges = pyg.EdgeSequence(
            right_1, right_2, right_3, right_4, right_5, top, crotch_top, crotch_bottom, left_top, left_middle, left_bottom
            ).close_loop()
        bottom = self.edges[-1]

        # Default placement
        self.set_pivot(crotch_bottom.end)
        self.translation = translation

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'outside': pyg.Interface(
                self, 
                pyg.EdgeSequence(right_1, right_2, right_3, right_4, right_5)),
            'crotch': pyg.Interface(self, pyg.EdgeSequence(crotch_top, crotch_bottom)),
            'inside': pyg.Interface(self, pyg.EdgeSequence(left_top, left_middle, left_bottom)),
            'bottom': pyg.Interface(self, bottom)
        }

        # Add top dart
        # NOTE: Ruffle indicator to match to waistline proportion for correct balance line matching
        if dart_width > 0:
            top_edges, int_edges = self.add_darts(
                top, dart_width, dart_depth, dart_position, double_dart=double_dart)
            self.interfaces['top'] = pyg.Interface(
                self, int_edges, 
                ruffle=waist / match_top_int_to if match_top_int_to is not None else 1.
            ) 
            self.edges.substitute(top, top_edges)
        else:
            self.interfaces['top'] = pyg.Interface(
                self, top, 
                ruffle=waist / match_top_int_to if match_top_int_to is not None else 1.
        ) 

    def add_darts(
            self,
            top: pyg.Edge,
            dart_width: float,
            dart_depth: float,
            dart_position: float,
            double_dart: bool = False
        ) -> tuple[pyg.EdgeSequence, pyg.EdgeSequence]:
        """Add dart(s) to the top edge of the panel.
        
        Creates one or two darts along the waistline edge to provide shaping
        for the difference between waist and hip measurements. When using
        double darts, the first dart is smaller (using SMALL_DART_DEPTH_RATIO).

        Parameters:
        -----------
        top : pyg.Edge
            The top edge (waistline) where darts will be inserted.
        dart_width : float
            Total width of the dart(s). For double darts, this is split in half.
        dart_depth : float
            Depth (length) of the dart(s) extending into the panel.
        dart_position : float
            Horizontal position of the dart(s) from the center of the edge,
            measured along the edge length.
        double_dart : bool, optional
            If True, creates two darts instead of one. The first dart is
            positioned slightly offset and uses a reduced depth.
            Default is False.

        Returns:
        --------
        top_edges : pyg.EdgeSequence
            New edge sequence representing the top edge with dart(s) inserted.
        int_edges : pyg.EdgeSequence
            Edge sequence containing the internal dart edges (the folded dart
            lines inside the panel).
        """
        
        if double_dart:
            dist = dart_position * self.DART_POSITION_MULTIPLIER  # Dist between darts -> dist between centers
            offsets_mid = [
                - dart_position + dist / 2 + dart_width / 2 + dart_width * self.DART_OFFSET_MULTIPLIER_QUARTER,   
                - dart_position - dist / 2 - dart_width * self.DART_OFFSET_MULTIPLIER_QUARTER,
            ]

            darts = [
                pyg.EdgeSeqFactory.dart_shape(dart_width / 2, dart_depth * self.SMALL_DART_DEPTH_RATIO), # smaller
                pyg.EdgeSeqFactory.dart_shape(dart_width / 2, dart_depth)
            ]
        else:
            offsets_mid = [
                - dart_position - dart_width / 2,
            ]
            darts = [
                pyg.EdgeSeqFactory.dart_shape(dart_width, dart_depth)
            ]

        top_edges, int_edges = pyg.EdgeSequence(top), pyg.EdgeSequence(top)

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
    """Half of a pants garment (left or right leg).
    
    A pants half consists of a front panel and a back panel, connected along
    the outside and inside seams. The front and back panels are positioned
    with different Z translations to create proper 3D shape.

    Attributes:
    -----------
    front : PantPanel
        The front panel of this pants half.
    back : PantPanel
        The back panel of this pants half.
    pants_design : PantsDesign
        The pants design parameters object containing all design measurements.
    BACK_HIPLINE_EXTENSION : float
        Multiplier for extending the back panel hipline for better fit.
    BACK_CROTCH_EXTENSION_OFFSET : float
        Additional crotch extension offset for the back panel (in cm).
    DEFAULT_PIVOT_OFFSET_X : float
        Default X-axis offset for panel pivot positioning.
    DEFAULT_TRANSLATION_Z_FRONT : float
        Default Z-axis translation for front panel positioning.
    DEFAULT_TRANSLATION_Z_BACK : float
        Default Z-axis translation for back panel positioning.
    """

    # Back panel constants
    BACK_HIPLINE_EXTENSION: float = 1.1
    BACK_CROTCH_EXTENSION_OFFSET: float = 3

    # Panel pivot and translation constants
    DEFAULT_PIVOT_OFFSET_X: float = -0.5
    DEFAULT_TRANSLATION_Z_FRONT: float = 25
    DEFAULT_TRANSLATION_Z_BACK: float = -20

    front: PantPanel
    back: PantPanel
    pants_design: PantsDesign
    
    def __init__(self,
                 tag: str,
                 design: dict,
                 ) -> None:
        """Initialize a pants half (left or right leg).
        
        Creates both front and back panels for one leg of the pants, calculates
        the rise measurements, and sets up the stitching rules to connect the
        panels along their seams.

        Parameters:
        -----------
        tag : str
            Side identifier: 'r' for right leg or 'l' for left leg.
        design : dict
            Design parameters dictionary. Must contain a 'pants' key with
            measurements including 'front_rise', 'back_rise', 'waist',
            'width_hips', 'length_waist_to_hip', and panel width/length values.

        Notes:
        ------
        The front and back panels are created with different parameters:
        - Back panel has extended hipline and additional crotch extension
        - Both panels use calculated rise measurements based on front and back rises
        - Panels are positioned with different Z translations for 3D shaping
        """
        super().__init__(design, tag)

        # Create PantsDesign from the design dict and store it
        self.pants_design = PantsDesign(design)
        
        rise_middle = (self.pants_design.back_rise + self.pants_design.front_rise) / 2
        hips_crotch_diff = rise_middle - self.pants_design.length_waist_to_hip

        self.front = PantPanel(
            name=f'pant_f_{tag}',
            design=self.pants_design,
            rise=self.pants_design.front_rise,
            mid_rise=rise_middle,
            waist=self.pants_design.waist / 2,
            hips=self.pants_design.width_hips / 2,
            hips_crotch_diff=hips_crotch_diff,
            crotch_extension=self.pants_design.width_hips / 8,
            crotch_hip_diff=rise_middle - self.pants_design.length_waist_to_hip,
            dart_position=self.pants_design.waist / 4,
            match_top_int_to=self.pants_design.waist / 2,
            translation=np.array([self.DEFAULT_PIVOT_OFFSET_X, 0, self.DEFAULT_TRANSLATION_Z_FRONT])
        )

        self.back = PantPanel(
            name=f'pant_b_{tag}',
            design=self.pants_design,
            rise=self.pants_design.back_rise,
            mid_rise=rise_middle,
            waist=self.pants_design.waist / 2,
            hips=self.pants_design.width_hips / 2,
            hips_crotch_diff=hips_crotch_diff,
            crotch_extension=self.pants_design.width_hips / 8 + self.BACK_CROTCH_EXTENSION_OFFSET,
            crotch_hip_diff=rise_middle - self.pants_design.length_waist_to_hip,
            hipline_ext=self.BACK_HIPLINE_EXTENSION,
            dart_position=self.pants_design.width_hips / 4,
            match_top_int_to=self.pants_design.waist / 2,
            double_dart=False,
            translation=np.array([self.DEFAULT_PIVOT_OFFSET_X, 0, self.DEFAULT_TRANSLATION_Z_BACK])
            )

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['outside'], self.back.interfaces['outside']),
            (self.front.interfaces['inside'], self.back.interfaces['inside'])
        )

        self.interfaces = {
            'crotch_f': self.front.interfaces['crotch'],
            'crotch_b': self.back.interfaces['crotch'],
            'top_f': self.front.interfaces['top'], 
            'top_b': self.back.interfaces['top'] 
        }

    def length(self) -> float:
        """Get the length of the pants half.
        
        Returns the length measurement of the front panel, which represents
        the overall length of this pants half from waist to hem.

        Returns:
        --------
        float
            The length of the pants half in the design units.
        """
        if self.pants_design.cuff.type:
            return self.front.length()
        
        return self.front.length()


class Pants(BaseBottoms):
    """Complete pants garment consisting of left and right halves.
    
    A full pants garment combines left and right pants halves, each containing
    front and back panels. The halves are mirrored and positioned based on body
    measurements, then connected at the front and back crotch seams.

    Attributes:
    -----------
    right : PantsHalf
        The right leg half of the pants.
    left : PantsHalf
        The left leg half of the pants (mirrored from right).
    body : BodyDefinition
        The body measurements object used for positioning the pants.
    """
    
    right: PantsHalf
    left: PantsHalf
    body: BodyDefinition

    def __init__(self, body: BodyDefinition, design: dict) -> None:
        """Initialize a complete pants garment.
        
        Creates both left and right pants halves, positions them based on body
        measurements, and sets up stitching rules to connect the halves at the
        crotch seams. The left half is created by mirroring the right half.

        Parameters:
        -----------
        body : BodyDefinition
            Body measurements object containing body parameters.
            Required parameters:
            - hips_line: Vertical position of the hips line
            - crotch_hip_diff: Vertical difference between crotch and hips
            - computed_waist_level: Vertical position of the waist level (computed property)
        design : dict
            Design parameters dictionary containing all measurements needed
            for constructing the pants panels.

        Notes:
        ------
        The pants are positioned vertically based on the body's waist level and
        crotch height. The left half is automatically mirrored from the right
        half to ensure symmetry. Interfaces are created for connecting to
        waistbands or other components at the top.
        """
        super().__init__(design)

        self.body = body

        # used for panel placement
        body_crotch_height = self.body.hips_line - self.body.crotch_hip_diff
        body_waist_level = self.body.computed_waist_level

        self.right = PantsHalf('r', design)
        self.right.translate_by([0, body_waist_level - body_crotch_height, 0])
        self.left = PantsHalf('l', design).mirror()
        self.left.translate_by([0, body_waist_level - body_crotch_height, 0])

        self.stitching_rules = pyg.Stitches(
            (self.right.interfaces['crotch_f'], self.left.interfaces['crotch_f']),
            (self.right.interfaces['crotch_b'], self.left.interfaces['crotch_b']),
        )

        self.interfaces = {
            'top_f': pyg.Interface.from_multiple(
                self.right.interfaces['top_f'], self.left.interfaces['top_f']),
            'top_b': pyg.Interface.from_multiple(
                self.right.interfaces['top_b'], self.left.interfaces['top_b']),
            # Some are reversed for correct connection
            'top': pyg.Interface.from_multiple(   # around the body starting from front right
                self.right.interfaces['top_f'].flip_edges(),
                self.left.interfaces['top_f'].reverse(with_edge_dir_reverse=True),
                self.left.interfaces['top_b'].flip_edges(),
                self.right.interfaces['top_b'].reverse(with_edge_dir_reverse=True), # Flips the edges and restores the direction
            )
        }

    def length(self) -> float:
        """Get the length of the pants garment.
        
        Returns the length measurement of the right pants half, which represents
        the overall length of the pants from waist to hem.

        Returns:
        --------
        float
            The length of the pants in the design units.
        """
        return self.right.length()
