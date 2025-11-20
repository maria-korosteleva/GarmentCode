from copy import deepcopy
from typing import Callable, Optional

import numpy as np

from garment_programs import weon_bands
import pygarment as pyg
from pattern_definitions.body_definition import BodyDefinition
from pattern_definitions.sleeve_design import SleeveDesign
from pattern_definitions.torso_design import TorsoDesign


# ------  Armhole shapes ------
def ArmholeSquare(
    incl: float,
    width: float,
    angle: float,
    invert: bool = True,
    **kwargs
) -> tuple:
    """Simple square armhole cut-out.
    
    Not recommended to use for sleeves, stitching in 3D might be hard.
    If angle is provided, it also calculates the shape of the sleeve interface to attach.
    
    Parameters
    ----------
    incl : float
        Inclination value.
    width : float
        Width of the armhole.
    angle : float
        Angle for the sleeve interface.
    invert : bool, optional
        Whether to invert the shape. Default is True.
    **kwargs
        Additional keyword arguments.
    
    Returns
    -------
    tuple
        Edge sequence and part to be preserved (inverted if requested).
    """

    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [incl, 0],  [incl, width])
    if not invert:
        return edges, None
    
    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyg.EdgeSeqFactory.from_verts(
        [incl + l*sina, - l*cosa], 
        [incl, 0],  [incl, width])
    
    # TODOLOW Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle) 

    return edges, sleeve_edges


def ArmholeAngle(
    incl: float,
    width: float,
    angle: float,
    incl_coeff: float = 0.2,
    w_coeff: float = 0.2,
    invert: bool = True,
    **kwargs
) -> tuple:
    """Piece-wise smooth armhole shape.
    
    Parameters
    ----------
    incl : float
        Inclination value.
    width : float
        Width of the armhole.
    angle : float
        Angle for the sleeve interface.
    incl_coeff : float, optional
        Inclination coefficient. Default is 0.2.
    w_coeff : float, optional
        Width coefficient. Default is 0.2.
    invert : bool, optional
        Whether to invert the shape. Default is True.
    **kwargs
        Additional keyword arguments.
    
    Returns
    -------
    tuple
        Edge sequence and part to be preserved (inverted if requested).
    """
    diff_incl = incl * (1 - incl_coeff)
    edges = pyg.EdgeSeqFactory.from_verts(
        [0, 0], [diff_incl, w_coeff * width], [incl, width])
    if not invert:
        return edges, None

    sina, cosa = np.sin(angle), np.cos(angle)
    l = edges[0].length()
    sleeve_edges = pyg.EdgeSeqFactory.from_verts(
        [diff_incl + l*sina, w_coeff * width - l*cosa], 
        [diff_incl, w_coeff * width],  [incl, width])
    # TODOLOW Bend instead of rotating to avoid sharp connection
    sleeve_edges.rotate(angle=-angle) 

    return edges, sleeve_edges


def ArmholeCurve(
    incl: float,
    width: float,
    angle: float,
    bottom_angle_mix: float = 0,
    invert: bool = True,
    verbose: bool = False,
    **kwargs
) -> tuple:
    """Classic sleeve opening on Cubic Bezier curves.
    
    Parameters
    ----------
    incl : float
        Inclination value.
    width : float
        Width of the armhole.
    angle : float
        Angle for the sleeve interface.
    bottom_angle_mix : float, optional
        Bottom angle mix factor. Default is 0.
    invert : bool, optional
        Whether to invert the shape. Default is True.
    verbose : bool, optional
        Whether to print verbose output. Default is False.
    **kwargs
        Additional keyword arguments.
    
    Returns
    -------
    tuple
        Edge sequence and part to be preserved (inverted if requested).
    """
    # Curvature as parameters?
    cps = [[0.5, 0.2], [0.8, 0.35]]
    edge = pyg.CurveEdge([incl, width], [0, 0], cps)
    edge_as_seq = pyg.EdgeSequence(edge.reverse())

    if not invert:
        return edge_as_seq, None
    
    # Initialize inverse (initial guess)
    # Agle == 0
    down_direction = np.array([0, -1])  # Full opening is vertically aligned
    inv_cps = deepcopy(cps)
    inv_cps[-1][1] *= -1  # Invert the last 
    inv_edge = pyg.CurveEdge(
        start=[incl, width], 
        end=(np.array([incl, width]) + down_direction * edge._straight_len()).tolist(), 
        control_points=inv_cps
    )

    # Rotate by desired angle (usually desired sleeve rest angle)
    inv_edge.rotate(angle=-angle)

    # Optimize the inverse shape to be nice
    shortcut = inv_edge.shortcut()
    rotated_direction = shortcut[-1] - shortcut[0]
    rotated_direction /= np.linalg.norm(rotated_direction)
    left_direction = np.array([-1, 0]) 
    mix_factor = bottom_angle_mix  
                                                          
    dir = (1 - mix_factor) * rotated_direction + (
        mix_factor * down_direction if mix_factor > 0 else (- mix_factor * left_direction))

    # TODOLOW Remember relative curvature results and reuse them? (speed)
    fin_inv_edge = pyg.ops.curve_match_tangents(
        inv_edge.as_curve(), 
        down_direction,  # Full opening is vertically aligned
        dir,
        target_len=edge.length(),
        return_as_edge=True, 
        verbose=verbose
    )

    return edge_as_seq, pyg.EdgeSequence(fin_inv_edge.reverse())


# -------- New sleeve definitions -------

class SleevePanel(pyg.Panel):
    """Trying proper sleeve panel"""
    
    # Class constants
    MIN_LENGTH: int = 5    # Minimum sleeve length
    
    # Class attributes
    sleeve_design: SleeveDesign

    def __init__(
        self,
        name: str,
        sleeve_design: SleeveDesign,
        open_shape: pyg.EdgeSequence,
        armhole_width: float,
        length_shift: float = 0,
        _standing_margin: int = 5
    ) -> None:
        """Define a standard sleeve panel (half a sleeve).
        
        Parameters
        ----------
        name : str
            Name of the panel.
        sleeve_design : SleeveDesign
            Design parameters dictionary.
        open_shape : pyg.EdgeSequence
            Edge sequence defining the sleeve opening shape.
        armhole_width : float
            Width of the armhole.
        length_shift : float, optional
            Force update sleeve length by this amount. Can be used to adjust
            length evaluation to fit the cuff. Default is 0.
        _standing_margin : int, optional
            Margin for standing shoulder. Default is 5.
        """
        super().__init__(name)

        # Create SleeveDesign from the design dict and store it
        self.sleeve_design = sleeve_design

        standing = self.sleeve_design.standing_shoulder

        end_width = self.sleeve_design.end_width

        # -- Main body of a sleeve --
        opening_length = abs(open_shape[0].start[0] - open_shape[-1].end[0])
        elbow_width = self.sleeve_design.elbow_width
        # Length from the border of the opening to the end of the sleeve
        length = self.sleeve_design.length - opening_length
        # NOTE: Asked to reduce by too much: reduce as much as possible
        length = max(length + length_shift, self.MIN_LENGTH)

        self.edges = pyg.EdgeSeqFactory.from_verts(
            [0, 0], [0, -end_width], [length / 2, -elbow_width], [length, -armhole_width]
        )

        # Align the opening
        open_shape.snap_to(self.edges[-1].end)
        open_shape[0].start = self.edges[-1].end   # chain
        self.edges.append(open_shape)
        # Fin
        self.edges.close_loop()

        if standing:
            raise NotImplementedError('Standing shoulder is not implemented yet')

        # Interfaces
        self.interfaces = {
            # NOTE: interface needs reversing because the open_shape was reversed for construction
            'in': pyg.Interface(self, open_shape, ruffle=self.sleeve_design.connect_ruffle),
            'out': pyg.Interface(self, self.edges[0], ruffle=self.sleeve_design.cuff.top_ruffle),
            'top': pyg.Interface(self, self.edges[-2:] if standing else self.edges[-1]),  
            'bottom': pyg.Interface(self, pyg.EdgeSequence(self.edges[1], self.edges[2]))
        }

        # Default placement
        self.set_pivot(self.edges[-1].start) 

    def length(self, longest_dim: bool = False) -> float:
        """Return the length of the sleeve panel.
        
        Parameters
        ----------
        longest_dim : bool, optional
            Whether to return the longest dimension (not used, for compatibility).
            Default is False.
        
        Returns
        design: dict,
        -------
        float
            Length of the sleeve panel.
        """
        return self.interfaces['bottom'].edges.length()


class Sleeve(pyg.Component):
    """Trying to do a proper sleeve"""
    
    # Class constants
    SLEEVE_Z_TRANSLATION: int = 15  # Translation in Z to separate front and back sleeves

    # Class attributes
    sleeve_design: SleeveDesign
    f_sleeve: Optional[SleevePanel]
    b_sleeve: Optional[SleevePanel]
    cuff: Optional[weon_bands.CuffBand]
    verbose: bool

    def __init__(
        self,
        tag: str,
        sleeve_design: SleeveDesign,
        shirt_design: TorsoDesign,
        front_w: float | Callable[[float], float],
        back_w: float | Callable[[float], float],
        front_hole_edge: pyg.Edge,
        back_hole_edge: pyg.Edge,
        adjusted_connecting_width: float,
    ) -> None:
        """Definition of a sleeve.
        
        Parameters
        ----------
        tag : str
            Tag for the sleeve component.
        sleeve_design : SleeveDesign
            Design parameters dictionary.
        shirt_design : TorsoDesign
            Design parameters dictionary.
        front_w : float | Callable[[float], float]
            Width of the front sleeve opening or a function to calculate it.
            Functions receive the requested vertical level and return the calculated width.
        back_w : float | Callable[[float], float]
            Width of the back sleeve opening or a function to calculate it.
            Functions receive the requested vertical level and return the calculated width.
        front_hole_edge : pyg.Edge
            Edge defining the front sleeve hole.
        back_hole_edge : pyg.Edge
            Edge defining the back sleeve hole.
        adjusted_connecting_width : Optional[float]
            Adjusted connecting width for sleeve calculations.
        """
        super().__init__(f'{self.__class__.__name__}_{tag}')

        self.sleeve_design = sleeve_design

        # Get shirt design for translation calculation
        x_sleeve_translation = - (shirt_design.neck_to_shoulder_distance**2 - shirt_design.shoulder_slant**2)**0.5
        x_sleeve_translation -= shirt_design.neck_width / 2
        armhole_width = shirt_design.scye_depth - shirt_design.shoulder_slant
        
        dist = ((front_hole_edge.start[0] - back_hole_edge.end[0])**2 + (front_hole_edge.start[1] - back_hole_edge.end[1])**2)**0.5
        dist_y = abs(front_hole_edge.start[1] - back_hole_edge.end[1])
        rest_angle = np.pi / 2 - np.arcsin(self.sleeve_design.bicep_width / dist) - np.arccos(dist_y / dist)

        smoothing_coeff = self.sleeve_design.smoothing_coeff

        front_w = front_w(adjusted_connecting_width) if callable(front_w) else front_w
        back_w = back_w(adjusted_connecting_width) if callable(back_w) else back_w

        # --- Define sleeve opening shapes ----
        # NOTE: Non-trad armholes only for sleeveless styles due to 
        # unclear inversion and stitching errors (see below)
        armhole = globals()[self.sleeve_design.armhole_shape] if self.sleeve_design.sleeveless else ArmholeCurve
        front_project, front_opening = armhole(
            front_w,
            armhole_width, 
            angle=rest_angle, 
            incl_coeff=smoothing_coeff, 
            w_coeff=smoothing_coeff, 
            invert=not self.sleeve_design.sleeveless,
            bottom_angle_mix=self.sleeve_design.opening_dir_mix,
            verbose=self.verbose
        )
        back_project, back_opening = armhole(
            back_w,
            armhole_width, 
            angle=rest_angle, 
            incl_coeff=smoothing_coeff, 
            w_coeff=smoothing_coeff,
            invert=not self.sleeve_design.sleeveless,
            bottom_angle_mix=self.sleeve_design.opening_dir_mix
        )
        
        self.interfaces = {
            'in_front_shape': pyg.Interface(self, front_project),
            'in_back_shape': pyg.Interface(self, back_project)
        }

        if self.sleeve_design.sleeveless:
            # The rest is not needed!
            return
        
        if front_w != back_w: 
            front_opening, back_opening = pyg.ops.even_armhole_openings(
                front_opening, back_opening, 
                tol=0.2 / front_opening.length(), # ~2mm tolerance as a fraction of length
                verbose=self.verbose
            )
        
        # --- Eval length adjustment for cuffs (if any) ----
        cuff_len_adj = self._cuff_len_adj()

        # ----- Get sleeve panels -------
        self.f_sleeve = SleevePanel(
            f'{tag}_sleeve_f', sleeve_design, front_opening,
            armhole_width=armhole_width,
            length_shift=-cuff_len_adj,
            ).translate_by([x_sleeve_translation, 0, self.SLEEVE_Z_TRANSLATION])
        self.b_sleeve = SleevePanel(
            f'{tag}_sleeve_b', sleeve_design, back_opening,
            armhole_width=armhole_width,
            length_shift=-cuff_len_adj,
            ).translate_by([x_sleeve_translation, 0, -self.SLEEVE_Z_TRANSLATION])

        # Connect panels
        self.stitching_rules = pyg.Stitches(
            (self.f_sleeve.interfaces['top'],
             self.b_sleeve.interfaces['top']),
            (self.f_sleeve.interfaces['bottom'],
             self.b_sleeve.interfaces['bottom']),
        )

        # Interfaces
        self.interfaces.update({
            'in': pyg.Interface.from_multiple(
                self.f_sleeve.interfaces['in'], 
                self.b_sleeve.interfaces['in'].reverse(with_edge_dir_reverse=True)
            ),
            'out': pyg.Interface.from_multiple(
                    self.f_sleeve.interfaces['out'], 
                    self.b_sleeve.interfaces['out']
                ),
        })

        # Cuff
        if self.sleeve_design.cuff.type:
            raise NotImplementedError('Cuffs are not implemented yet')

        # Set label 
        self.set_panel_label('arm')

    def _cuff_len_adj(self) -> float:
        """Evaluate sleeve length adjustment due to cuffs (if any).
        
        Returns
        -------
        float
            Length adjustment for the cuff, or 0 if no cuff.
        """
        if not self.sleeve_design.cuff.type:
            return 0
        
        raise NotImplementedError('Cuffs are not implemented yet')

    def length(self) -> float:
        """Return the length of the sleeve including cuff (if any).
        
        Returns
        -------
        float
            Total length of the sleeve, including cuff if present.
        """
        if self.sleeve_design.sleeveless:
            return 0
        
        if self.sleeve_design.cuff.type:
            if self.cuff is not None:
                return self.f_sleeve.length() + self.cuff.length()
            else:
                raise ValueError('Cuff is not defined, but cuff type is set in the design')
        
        return self.f_sleeve.length()