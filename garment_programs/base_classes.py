import math
from typing import Callable, Optional, Any, List, Protocol

import pygarment as pyg

from garment_programs.garment_enums import InterfaceName
from pattern_definitions.torso_design import TorsoDesign
from pattern_definitions.body_definition import BodyDefinition
from config import AttachmentConstraint


class VertexProcessorProvider(Protocol):
    """Protocol for garment programs that provide vertex processor callbacks."""
    
    def get_vertex_processor_callback(self) -> Callable[[Any, list[int], Any], list[int]] | None:
        """Get the vertex processor callback for attachment constraints.
        
        Returns:
        --------
        Callable[[EdgeLabel, list[int], BoxMesh], list[int]] | None
            A callback function that processes reference vertices, or None.
        """
        ...

class BaseBodicePanel(pyg.Panel):
    """Base class for bodice panels that defines expected interfaces and common functions"""
    
    # Class attributes
    neck_to_shoulder_delta_x: float
    neck_width: float
    torso_design: TorsoDesign

    def __init__(self,
                 name: str,
                 torso_design: TorsoDesign
                 ) -> None:
        super().__init__(name)
        self.torso_design = torso_design
        self.neck_to_shoulder_delta_x = math.sqrt(torso_design.neck_to_shoulder_distance ** 2 - torso_design.shoulder_slant ** 2)
        self.neck_width = torso_design.neck_width
        
        self.interfaces = {
            InterfaceName.OUTSIDE: object(),
            InterfaceName.INSIDE: object(),
            InterfaceName.SHOULDER: object(),
            InterfaceName.BOTTOM: object(),

            InterfaceName.SHOULDER_CORNER: object(),
            InterfaceName.COLLAR_CORNER: object(),
        }

    def get_width(self, level: float) -> float:
        """Return the panel width at a given level (excluding darts)
           * Level is counted from the top of the panel
        
        NOTE: for fitted bodice, the request is only valid for values between 0 and bust_level
        """
        # NOTE: this evaluation assumes that the top edge width is the same as bodice shoulder width 
        side_edge = self.interfaces[InterfaceName.OUTSIDE].edges[-1]

        x = side_edge.end[0] - side_edge.start[0]
        y = side_edge.end[1] - side_edge.start[1]

        # If the orientation of the edge is "looking down"
        # instead of "looking up" as calculations above expect, flip the values
        if y < 0:
            x, y = -x, -y

        return (level * x / y) + self.neck_to_shoulder_delta_x + self.neck_width / 2


class BaseBottoms(pyg.Component):
    """A base class for all the bottom components.
        Defines common elements: 
        * List of interfaces
        * Presence of the rise value
    """
    # Class attributes
    body: Optional[BodyDefinition]
    
    def __init__(self, tag: str = '') -> None:
        """Base bottoms initialization
        """
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')
        
        # Set of interfaces that need to be implemented
        self.interfaces = {
            InterfaceName.TOP: object()
        }
    
    @staticmethod
    def get_attachment_constraints() -> List[AttachmentConstraint]:
        """Get the list of attachment constraints for this garment.
        
        Default implementation returns an empty list. Subclasses should override
        this method to return garment-specific constraints.
        
        Returns:
        --------
        List[AttachmentConstraint]
            An empty list by default. Subclasses should override to return
            garment-specific constraints.
        """
        return []
        
class StackableSkirtComponent(BaseBottoms):
    """
        Abstract definition of a skirt that can be stacked with other stackable skirts
        (connecting bottom to another StackableSkirtComponent())
    """
    # Class attributes
    body: BodyDefinition
    skirt_design: Any  # Will be SkirtDesign when imported
    length_override: Optional[float]
    slit: bool
    top_ruffles: bool

    def __init__(self, tag: str = '') -> None:
        """Skirt initialization.

        Parameters:
        -----------
        tag : str, optional
            Tag identifier for the skirt component. Default is ''.
        """
        # BaseBottoms only accepts tag
        super().__init__(tag=tag)

        # Set of interfaces that need to be implemented
        self.interfaces = {
            InterfaceName.TOP: object(),
            InterfaceName.BOTTOM_F: object(),
            InterfaceName.BOTTOM_B: object(),
            InterfaceName.BOTTOM: object()
        }


class BaseBand(pyg.Component):
    # Class attributes
    body: Optional[BodyDefinition]
    design: Optional[Any]
    rise: Optional[float]
    
    def __init__(
        self,
        body: Optional[BodyDefinition],
        design: Optional[Any],
        tag: str = '',
        rise: Optional[float] = None
    ) -> None:
        """Base band initialization
        """
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')
        self.body = body
        self.design = design
        self.rise = rise
        
        # Set of interfaces that need to be implemented
        self.interfaces = {
            InterfaceName.TOP: object(),
            InterfaceName.BOTTOM: object()
        }

    def length(self) -> float:
        """Base length == Length of a first panel"""
        return self._get_subcomponents()[0].length()
    
    @staticmethod
    def get_attachment_constraints() -> List[AttachmentConstraint]:
        """Get the list of attachment constraints for this garment.
        
        Default implementation returns an empty list. Subclasses should override
        this method to return garment-specific constraints.
        
        Returns:
        --------
        List[AttachmentConstraint]
            An empty list by default. Subclasses should override to return
            garment-specific constraints.
        """
        return []
    
    def get_vertex_processor_callback(self):
        """Get the vertex processor callback for attachment constraints.
        
        This callback is used by BoxMesh to process attachment constraints and
        determine the final set of vertices to label. The callback handles all
        constraint-specific logic internally, including getting constraints from
        the garment program.
        
        Default implementation returns None (no processing).
        Subclasses should override this method to provide garment-specific
        vertex processing logic.
        
        Returns:
        --------
        Callable[[BoxMesh], None] | None
            A callback function that takes (box_mesh) and processes constraints
            internally. The callback should:
            - Get constraints from the garment class's get_attachment_constraints() static method
            - Process each constraint to find/label vertices
            - Store constraints in box_mesh.attachment_constraints
            Returns None if no processing is needed.
        """
        return None