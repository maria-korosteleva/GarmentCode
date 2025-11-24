from typing import Optional, Union, List

import numpy as np
import pygarment as pyg

from garment_programs.base_classes import StackableSkirtComponent
from garment_programs.garment_enums import InterfaceName, EdgeLabel
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.skirt_design import SkirtDesign
from config import AttachmentConstraint


class CircleArcPanel(pyg.Panel):
    """One panel circle skirt"""

    # Calculation constants
    QUARTER_CIRCLE_RAD: float = np.pi / 2
    
    # Class attributes
    waist_width: float

    def __init__(
        self,
        name: str,
        top_rad: float,
        length: float,
        angle: float,
        match_top_int_proportion: Optional[float] = None,
        match_bottom_int_proportion: Optional[float] = None
    ) -> None:
        """
        A single panel for a circle skirt, defined by a top radius, length, and angle.

        Parameters
        ----------
        name : str
            Name of the panel.
        top_rad : float
            Radius of the top (waist) arc.
        length : float
            Length of the skirt panel from top to bottom.
        angle : float
            The angle of the arc in radians.
        match_top_int_proportion : float, optional
            The target length for the top interface to calculate the ruffle factor, by default None.
        match_bottom_int_proportion : float, optional
            The target length for the bottom interface to calculate the ruffle factor, by default None.
        """
        super().__init__(name)

        self.waist_width = angle * top_rad
        halfarc = angle / 2

        dist_w = 2 * top_rad * np.sin(halfarc)
        dist_out = 2 * (top_rad + length) * np.sin(halfarc)

        vert_len = length * np.cos(halfarc)

        # top
        self.edges.append(pyg.CircleEdgeFactory.from_points_radius(
            [-dist_w/2, 0], [dist_w/2, 0], 
            radius=top_rad, large_arc=halfarc > self.QUARTER_CIRCLE_RAD))

        self.edges.append(pyg.Edge(
            self.edges[-1].end, [dist_out / 2, -vert_len]))
        
        # Bottom
        self.edges.append(pyg.CircleEdgeFactory.from_points_radius(
            self.edges[-1].end, [- dist_out / 2, -vert_len], 
            radius=top_rad + length,
            large_arc=halfarc > self.QUARTER_CIRCLE_RAD, right=False))

        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            InterfaceName.TOP: pyg.Interface(self, self.edges[0],
                                 ruffle=self.edges[0].length() / match_top_int_proportion if match_top_int_proportion is not None else 1.
                                 ).reverse(True),
            InterfaceName.BOTTOM: pyg.Interface(self, self.edges[2],
                                    ruffle=self.edges[2].length() / match_bottom_int_proportion if match_bottom_int_proportion is not None else 1.
                                    ),
            InterfaceName.LEFT: pyg.Interface(self, self.edges[1]),
            InterfaceName.RIGHT: pyg.Interface(self, self.edges[3])
        }

    def length(self, *args) -> float:
        """Return the length of the panel (right edge).
        
        Returns
        -------
        float
            Length of the panel's right edge.
        """
        return self.interfaces[InterfaceName.RIGHT].edges.length()
    
    @staticmethod
    def from_w_length_suns(
        name: str,
        length: float,
        top_width: float,
        bottom_width: float,
        **kwargs
    ) -> 'CircleArcPanel':
        radius = length / (1 - top_width / bottom_width)
        angle = bottom_width / radius

        return CircleArcPanel(name=name, top_rad=radius - length, length=length, angle=angle, **kwargs)


class AsymHalfCirclePanel(pyg.Panel):
    """Panel for a asymmetrci circle skirt"""

    def __init__(
        self,
        name: str,
        top_rad: float,
        length_f: float,
        length_s: float,
        match_top_int_proportion: Optional[float] = None,
        match_bottom_int_proportion: Optional[float] = None
    ) -> None:
        """ 
        A panel for an asymmetric circle skirt, creating a half-circle arc.

        Parameters
        ----------
        name : str
            Name of the panel.
        top_rad : float
            Radius of the top (waist) arc.
        length_f : float
            Length at the front (center) of the panel.
        length_s : float
            Length at the side of the panel.
        match_top_int_proportion : float, optional
            The target length for the top interface to calculate the ruffle factor, by default None.
        match_bottom_int_proportion : float, optional
            The target length for the bottom interface to calculate the ruffle factor, by default None.
        """
        super().__init__(name)

        dist_w = 2 * top_rad 
        dist_out = 2 * (top_rad + length_s)

        # top
        self.edges.append(pyg.CircleEdgeFactory.from_points_radius(
            [-dist_w/2, 0], [dist_w/2, 0], 
            radius=top_rad, large_arc=False))

        self.edges.append(pyg.Edge(
            self.edges[-1].end, [dist_out / 2, 0]))
        
        # Bottom
        self.edges.append(
            pyg.CircleEdgeFactory.from_three_points(
                self.edges[-1].end, [- dist_out / 2, 0], 
                point_on_arc=[0, -(top_rad + length_f)]
            )
        )

        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            InterfaceName.TOP: pyg.Interface(self, self.edges[0],
                                 ruffle=self.edges[0].length() / match_top_int_proportion if match_top_int_proportion is not None else 1.
                                 ).reverse(True),
            InterfaceName.BOTTOM: pyg.Interface(self, self.edges[2],
                                    ruffle=self.edges[2].length() / match_bottom_int_proportion if match_bottom_int_proportion is not None else 1.
                                    ),
            InterfaceName.LEFT: pyg.Interface(self, self.edges[1]),
            InterfaceName.RIGHT: pyg.Interface(self, self.edges[3])
        }
    
    def length(self, *args) -> float:
        """Return the length of the panel (right edge).
        
        Returns
        -------
        float
            Length of the panel's right edge.
        """
        return self.interfaces[InterfaceName.RIGHT].edges.length()

class SkirtCircle(StackableSkirtComponent):
    """Simple circle skirt"""

    # Class constants
    MIN_LENGTH: int = 5
    FRONT_TRANSLATION_Z: int = 15
    BACK_TRANSLATION_Z: int = -15
    FULL_CIRCLE_RAD: float = 2 * np.pi
    
    # Class attributes
    skirt_design: SkirtDesign
    slit: bool
    waist_front: float
    waist_back: float
    front: CircleArcPanel
    back: CircleArcPanel

    def __init__(
        self,
        skirt_design: SkirtDesign,
        waist_front: float,
        waist_back: float,
        tag: str = '',
        length: Optional[float] = None,
        slit: bool = True,
        asymm: bool = False,
        min_len: Optional[int] = None,
        **kwargs
    ) -> None:
        """Initialize a simple circle skirt component. Can be symmetric or asymmetric.

        Parameters
        ----------
        skirt_design : SkirtDesign
            Skirt design parameters object.
        waist_front : float
            Front waist measurement (waist - waist_back_width).
        waist_back : float
            Back waist measurement (waist_back_width).
        tag : str, optional
            A tag for the component name (e.g., 'r' or 'l'). Default is ''.
        length : float, optional
            Overrides the length from the design dictionary. Default is None.
        slit : bool, optional
            Whether to add a cut/slit to the skirt. Default is True.
        asymm : bool, optional
            If True, creates an asymmetric skirt. Default is False.
        min_len : int, optional
            Minimum length for the skirt. Default is None.
        **kwargs
            Additional keyword arguments.
        """
        super().__init__(tag=tag)

        # Store design and waist measurements
        self.skirt_design = skirt_design
        self.slit = slit
        self.waist_front = waist_front
        self.waist_back = waist_back
        
        bottom_width = self.skirt_design.bottom_width
        skirt_length = max(self.skirt_design.length, self.MIN_LENGTH) if length is None else length
        waist = self.skirt_design.waist_width

        # panels (created without body positioning - will be applied in apply_body_alignment)
        if not asymm:  # Typical symmetric skirt
            self.front = CircleArcPanel.from_w_length_suns(
                f'skirt_front_{tag}' if tag else 'skirt_front', 
                skirt_length, waist, bottom_width,
                match_top_int_proportion=waist_front,
            ).translate_by([0, 0, self.FRONT_TRANSLATION_Z])

            self.back = CircleArcPanel.from_w_length_suns(
                f'skirt_back_{tag}'  if tag else 'skirt_back', 
                skirt_length, waist, bottom_width,
                match_top_int_proportion=waist_back,
            ).translate_by([0, 0, self.BACK_TRANSLATION_Z])
        else:
            # NOTE: Asymmetic front/back is only defined on full skirt (1 sun)
            w_rad = waist / self.FULL_CIRCLE_RAD
            f_length = self.skirt_design.asymm.front_length * skirt_length
            tot_len = w_rad * 2 + skirt_length + f_length 
            del_r = tot_len / 2 - f_length - w_rad
            s_length = np.sqrt((tot_len / 2)**2 - del_r**2) - w_rad

            self.front = AsymHalfCirclePanel(
                f'skirt_front_{tag}' if tag else 'skirt_front', 
                w_rad, f_length, s_length,
                match_top_int_proportion=waist_front,
            ).translate_by([0, 0, self.FRONT_TRANSLATION_Z])

            self.back = AsymHalfCirclePanel(
                f'skirt_back_{tag}'  if tag else 'skirt_back', 
                w_rad, skirt_length, s_length,
                match_top_int_proportion=waist_back,
            ).translate_by([0, 0, self.BACK_TRANSLATION_Z])

        # Add a cut
        if self.skirt_design.cut.add and slit:
            self.add_cut(
                self.front if self.skirt_design.cut.place > 0 else self.back, 
                self.skirt_design, skirt_length)

        # Stitches
        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces[InterfaceName.RIGHT], self.back.interfaces[InterfaceName.RIGHT]),
            (self.front.interfaces[InterfaceName.LEFT], self.back.interfaces[InterfaceName.LEFT])
        )

        # Interfaces
        self.interfaces = {
            InterfaceName.TOP: pyg.Interface.from_multiple(self.front.interfaces[InterfaceName.TOP], self.back.interfaces[InterfaceName.TOP]),
            InterfaceName.BOTTOM_F: self.front.interfaces[InterfaceName.BOTTOM],
            InterfaceName.BOTTOM_B: self.back.interfaces[InterfaceName.BOTTOM],
            InterfaceName.BOTTOM: pyg.Interface.from_multiple(self.front.interfaces[InterfaceName.BOTTOM], self.back.interfaces[InterfaceName.BOTTOM])
        }
        
        # Add lower_interface label for attachment constraints
        self.interfaces[InterfaceName.TOP].edges.propagate_label(EdgeLabel.LOWER_INTERFACE)
        
    def add_cut(
        self,
        panel: Union[CircleArcPanel, 'AsymHalfCirclePanel'],
        skirt_design: SkirtDesign,
        skirt_length: float
    ) -> None:
        """Add a cut to the skirt.
        
        Parameters
        ----------
        panel : CircleArcPanel | AsymHalfCirclePanel
            The panel to add the cut to.
        skirt_design : SkirtDesign
            Skirt design parameters object containing cut specifications.
        skirt_length : float
            Length of the skirt (used for calculating cut dimensions).
        """
        width, depth = skirt_design.cut.width * skirt_length, skirt_design.cut.depth * skirt_length

        target_edge = panel.interfaces[InterfaceName.BOTTOM].edges[0]
        t_len = target_edge.length()
        offset = abs(skirt_design.cut.place * t_len)

        # Respect the placement boundaries
        offset = max(offset, width / 2)
        offset = min(offset, t_len - width / 2)

        # NOTE: heuristic is specific for the panels that we use
        right = target_edge.start[0] > target_edge.end[0]

        # Make a cut
        cut_shape = pyg.EdgeSeqFactory.dart_shape(width, depth=depth)

        new_edges, _, interf_edges = pyg.ops.cut_into_edge(
            cut_shape, target_edge, 
            offset=offset, 
            right=right
        )

        panel.edges.substitute(target_edge, new_edges)
        panel.interfaces[InterfaceName.BOTTOM].substitute(
            target_edge, interf_edges,
            [panel for _ in range(len(interf_edges))])
        
    def length(self, *args) -> float:
        """Return the length of the skirt.
        
        Returns
        -------
        float
            Length of the skirt.
        """
        return self.front.length()

    def get_waist_width(self) -> float:
        """Return the waist width of the skirt.
        
        Returns
        -------
        float
            Waist width of the skirt.
        """
        return self.front.waist_width

    def get_attachment_constraints(self) -> List[AttachmentConstraint]:
        """Get the list of attachment constraints for this skirt garment.
        
        Returns the attachment constraints required for simulating this skirt garment.
        Skirts require a lower_interface constraint at the waist level.
        
        Returns:
        --------
        List[AttachmentConstraint]
            A list containing the lower_interface attachment constraint for skirts.
        """
        lower_interface_constraint = AttachmentConstraint(
            label='lower_interface',
            stiffness=0.0,
            damping=10.0,
            position_calculation={
                'x': {'positive': [], 'negative': []},
                'y': {
                    'positive': ['computed_waist_level'],
                    'negative': []
                },
                'z': {'positive': [], 'negative': []}
            },
            direction=None  # Will use default [0, 1, 0] (upward)
        )
        
        return [lower_interface_constraint]

    def apply_body_alignment(self, body: BodyDefinition) -> None:
        """Apply body alignment to position the skirt correctly.
        
        Translates the skirt garment vertically based on the body's waist
        level to ensure proper fit and alignment.
        
        Parameters
        ----------
        body : BodyDefinition
            Body measurements object containing body parameters.
            Required parameters:
            - computed_waist_level: Vertical position of the waist level (computed property)
        """
        waist_level = body.computed_waist_level
        
        # Position front and back panels at waist level
        self.front.translate_by([0, waist_level, 0])
        self.back.translate_by([0, waist_level, 0])

class AsymmSkirtCircle(SkirtCircle):
    """Front/back asymmetric skirt."""
    
    def __init__(
        self,
        skirt_design: SkirtDesign,
        waist_front: float,
        waist_back: float,
        tag: str = '',
        length: Optional[float] = None,
        slit: bool = True,
        **kwargs
    ) -> None:
        """Initialize a front/back asymmetric skirt.
        
        Parameters
        ----------
        skirt_design : SkirtDesign
            Skirt design parameters object.
        waist_front : float
            Front waist measurement (waist - waist_back_width).
        waist_back : float
            Back waist measurement (waist_back_width).
        tag : str, optional
            A tag for the component name. Default is ''.
        length : float, optional
            Overrides the length from the design dictionary. Default is None.
        slit : bool, optional
            Whether to add a cut/slit to the skirt. Default is True.
        **kwargs
            Additional keyword arguments.
        """
        super().__init__(skirt_design, waist_front, waist_back, tag, length, slit, asymm=True)