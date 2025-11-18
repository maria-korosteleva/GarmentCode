from typing import Optional

import numpy as np
import pygarment as pyg

from garment_programs.base_classes import StackableSkirtComponent
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.skirt_design import SkirtDesign


class CircleArcPanel(pyg.Panel):
    """One panel circle skirt"""

    # Calculation constants
    QUARTER_CIRCLE_RAD = np.pi / 2

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
            'top': pyg.Interface(self, self.edges[0],
                                 ruffle=self.edges[0].length() / match_top_int_proportion if match_top_int_proportion is not None else 1.
                                 ).reverse(True),
            'bottom': pyg.Interface(self, self.edges[2],
                                    ruffle=self.edges[2].length() / match_bottom_int_proportion if match_bottom_int_proportion is not None else 1.
                                    ),
            'left': pyg.Interface(self, self.edges[1]),
            'right': pyg.Interface(self, self.edges[3])
        }

    def length(self, *args) -> float:
        """Return the length of the panel (right edge).
        
        Returns
        -------
        float
            Length of the panel's right edge.
        """
        return self.interfaces['right'].edges.length()
    
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
            'top': pyg.Interface(self, self.edges[0],
                                 ruffle=self.edges[0].length() / match_top_int_proportion if match_top_int_proportion is not None else 1.
                                 ).reverse(True),
            'bottom': pyg.Interface(self, self.edges[2],
                                    ruffle=self.edges[2].length() / match_bottom_int_proportion if match_bottom_int_proportion is not None else 1.
                                    ),
            'left': pyg.Interface(self, self.edges[1]),
            'right': pyg.Interface(self, self.edges[3])
        }
    
    def length(self, *args) -> float:
        """Return the length of the panel (right edge).
        
        Returns
        -------
        float
            Length of the panel's right edge.
        """
        return self.interfaces['right'].edges.length()

class SkirtCircle(StackableSkirtComponent):
    """Simple circle skirt"""

    MIN_LENGTH = 5

    # Panel placement constants
    FRONT_TRANSLATION_Z = 15
    BACK_TRANSLATION_Z = -15

    # Asymmetric calculation constants
    FULL_CIRCLE_RAD = 2 * np.pi

    def __init__(
        self,
        body: BodyDefinition | dict,
        design: dict,
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
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
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
        super().__init__(body, design, tag)

        # Create SkirtDesign from the design dict and store it
        self.skirt_design = SkirtDesign(design)
        
        bottom_width = self.skirt_design.bottom_width
        length = max(self.skirt_design.length, self.MIN_LENGTH) if length is None else length
        waist = self.skirt_design.waist_width

        # panels
        if not asymm:  # Typical symmetric skirt
            self.front = CircleArcPanel.from_w_length_suns(
                f'skirt_front_{tag}' if tag else 'skirt_front', 
                length, waist, bottom_width,
                match_top_int_proportion=self.body['waist'] - self.body['waist_back_width'],
                ).translate_by([0, body['_waist_level'], self.FRONT_TRANSLATION_Z])

            self.back = CircleArcPanel.from_w_length_suns(
                f'skirt_back_{tag}'  if tag else 'skirt_back', 
                length, waist, bottom_width,
                match_top_int_proportion=self.body['waist_back_width'],
                ).translate_by([0, body['_waist_level'], self.BACK_TRANSLATION_Z])
        else:
            # NOTE: Asymmetic front/back is only defined on full skirt (1 sun)
            w_rad = waist / self.FULL_CIRCLE_RAD
            f_length = self.skirt_design.asymm.front_length * length
            tot_len = w_rad * 2 + length + f_length 
            del_r = tot_len / 2 - f_length - w_rad
            s_length = np.sqrt((tot_len / 2)**2 - del_r**2) - w_rad

            self.front = AsymHalfCirclePanel(
                f'skirt_front_{tag}' if tag else 'skirt_front', 
                w_rad, f_length, s_length,
                match_top_int_proportion=self.body['waist'] - self.body['waist_back_width'],
                ).translate_by([0, body['_waist_level'], self.FRONT_TRANSLATION_Z])

            self.back = AsymHalfCirclePanel(
                f'skirt_back_{tag}'  if tag else 'skirt_back', 
                w_rad, length, s_length,
                match_top_int_proportion=self.body['waist_back_width'],
                ).translate_by([0, body['_waist_level'], self.BACK_TRANSLATION_Z])

        # Add a cut
        if self.skirt_design.cut.add and slit:
            self.add_cut(
                self.front if self.skirt_design.cut.place > 0 else self.back, 
                self.skirt_design, length)

        # Stitches
        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Interfaces
        self.interfaces = {
            'top': pyg.Interface.from_multiple(self.front.interfaces['top'], self.back.interfaces['top']),
            'bottom_f': self.front.interfaces['bottom'],
            'bottom_b': self.back.interfaces['bottom'],
            'bottom': pyg.Interface.from_multiple(self.front.interfaces['bottom'], self.back.interfaces['bottom'])
        }
        
        # Add lower_interface label for attachment constraints
        self.interfaces['top'].edges.propagate_label('lower_interface')
        
    def add_cut(
        self,
        panel: CircleArcPanel | AsymHalfCirclePanel,
        skirt_design: SkirtDesign,
        sk_length: float
    ) -> None:
        """Add a cut to the skirt.
        
        Parameters
        ----------
        panel : CircleArcPanel | AsymHalfCirclePanel
            The panel to add the cut to.
        skirt_design : SkirtDesign
            Skirt design parameters object containing cut specifications.
        sk_length : float
            Length of the skirt (used for calculating cut dimensions).
        """
        width, depth = skirt_design.cut.width * sk_length, skirt_design.cut.depth * sk_length

        target_edge = panel.interfaces['bottom'].edges[0]
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
        panel.interfaces['bottom'].substitute(
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

class AsymmSkirtCircle(SkirtCircle):
    """Front/back asymmetric skirt."""
    
    def __init__(
        self,
        body: BodyDefinition | dict,
        design: dict,
        tag: str = '',
        length: Optional[float] = None,
        slit: bool = True,
        **kwargs
    ) -> None:
        """Initialize a front/back asymmetric skirt.
        
        Parameters
        ----------
        body : BodyDefinition | dict
            Body measurements object or dictionary.
        design : dict
            Design parameters dictionary.
        tag : str, optional
            A tag for the component name. Default is ''.
        length : float, optional
            Overrides the length from the design dictionary. Default is None.
        slit : bool, optional
            Whether to add a cut/slit to the skirt. Default is True.
        **kwargs
            Additional keyword arguments.
        """
        super().__init__(body, design, tag, length, slit, asymm=True)