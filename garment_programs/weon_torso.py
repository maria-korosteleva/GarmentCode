"""Panels for a straight upper garment (T-shirt).

Note that the code is very similar to Bodice.
"""

import numpy as np
import pygarment as pyg

from garment_programs.base_classes import BaseBodicePanel
from pattern_definitions.torso_design import TorsoDesign
from pattern_definitions.shirt_design import ShirtDesign


class TorsoFrontHalfPanel(BaseBodicePanel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    # Class attributes
    width: float
    
    def __init__(
        self,
        name: str,
        shirt_design: ShirtDesign,
    ) -> None:
        """Create a front half panel for a simple upper garment (e.g. T-Shirt).
        
        Parameters
        ----------
        name : str
            Name of the panel.
        Shirt_design : ShirtDesign
            Shirt design parameters.
        """
        super().__init__(name, shirt_design.torso_design)

        # sizes   
        waist = self.torso_design.width_waist / 2
        bust = self.torso_design.width_chest / 2
        self.width = self.torso_design.width_chest / 2
        max_len = self.torso_design.front_length

        bottom = pyg.Edge(
            start=[0, 0], 
            end=[-self.torso_design.width_hip / 2, 0],
        )
        right_bottom = pyg.CurveEdgeFactory.curve_from_tangents(
            start=bottom.end,
            end=[-waist, max_len - self.torso_design.waist_over_bust_line_height],
            target_tan1=np.array([0, 1]),
        )
        right_middle = pyg.CurveEdgeFactory.curve_from_tangents(
            start=right_bottom.end,
            end=[-bust, max_len - self.torso_design.scye_depth],
            target_tan0=np.array([0, 1]),
        )

        self.edges.append([bottom, right_bottom, right_middle])
        self.edges.append(pyg.EdgeSeqFactory.from_verts(
            right_middle.end,
            [-bust, max_len - self.torso_design.shoulder_slant], 
            [0, max_len]
        ))
        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            'outside':  pyg.Interface(self, pyg.EdgeSequence(right_bottom, right_middle)),   
            'inside': pyg.Interface(self, self.edges[-1]),
            'shoulder': pyg.Interface(self, self.edges[-2]),
            'bottom': pyg.Interface(self, bottom),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyg.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyg.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, - max_len, 0])

    def get_width(self, level: float) -> float:
        """Get the width of the panel at a given level"""
        return super().get_width(level) + self.width - self.neck_to_shoulder_delta_x - self.torso_design.neck_width / 2


class TorsoBackHalfPanel(BaseBodicePanel):
    """ Half of a simple non-fitted upper garment (e.g. T-Shirt) """
    # Class attributes
    width: float
    
    def __init__(
        self,
        name: str,
        shirt_design: ShirtDesign,
        match_length_to_front: bool = True
    ) -> None:
        """Create a back half panel for a simple upper garment (e.g. T-Shirt).
        
        Parameters
        ----------
        name : str
            Name of the panel.
        shirt_design : ShirtDesign
            Shirt design parameters.
        match_length_to_front : bool, optional
            Whether to match the back length to the front length.
            Default is True.
        """
        super().__init__(name, shirt_design.torso_design)

        # sizes   
        waist = self.torso_design.width_waist / 2
        bust = self.torso_design.width_chest / 2
        self.width = self.torso_design.width_chest / 2
        if not match_length_to_front:
            max_len = self.torso_design.back_length
            bottom = pyg.Edge(
                start=[0, 0], 
                end=[-self.torso_design.width_hip / 2, 0],
            )
        else:
            max_len = self.torso_design.front_length
            bottom = pyg.CurveEdgeFactory.curve_from_tangents(
                start=[0, max_len - self.torso_design.back_length],
                end=[-self.torso_design.width_hip / 2, 0],
                target_tan0=np.array([-1, 0]),
            )

        right_bottom = pyg.CurveEdgeFactory.curve_from_tangents(
            start=bottom.end,
            end=[-waist, max_len - self.torso_design.waist_over_bust_line_height],
            target_tan1=np.array([0, 1]),
        )
        right_middle = pyg.CurveEdgeFactory.curve_from_tangents(
            start=right_bottom.end,
            end=[-bust, max_len - self.torso_design.scye_depth],
            target_tan0=np.array([0, 1]),
        )

        self.edges.append([bottom, right_bottom, right_middle])
        self.edges.append(pyg.EdgeSeqFactory.from_verts(
            right_middle.end,
            [-bust, max_len - self.torso_design.shoulder_slant], 
            [0, max_len]
        ))
        self.edges.close_loop()

        # Interfaces
        self.interfaces = {
            'outside':  pyg.Interface(self, pyg.EdgeSequence(right_bottom, right_middle)),   
            'inside': pyg.Interface(self, self.edges[-1]),
            'shoulder': pyg.Interface(self, self.edges[-2]),
            'bottom': pyg.Interface(self, bottom),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyg.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyg.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, - max_len, 0])

    def get_width(self, level: float) -> float:
        """Get the width of the panel at a given level"""
        return super().get_width(level) + self.width - self.neck_to_shoulder_delta_x - self.torso_design.neck_width / 2
