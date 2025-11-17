import math

import pygarment as pyg

class BaseBodicePanel(pyg.Panel):
    """Base class for bodice panels that defines expected interfaces and common functions"""
    def __init__(self, name, body, design) -> None:
        super().__init__(name)
        self.neck_to_shoulder_delta_x = math.sqrt(design['neck_to_shoulder_distance']['v'] ** 2 - design['shoulder_slant']['v'] ** 2)
        self.neck_width = design['neck_width']['v']
        self.body = body
        self.design = design
        
        self.interfaces = {
            'outside': object(),
            'inside': object(),
            'shoulder': object(),
            'bottom': object(),

            'shoulder_corner': object(),
            'collar_corner': object(),
        }

    def get_width(self, level):
        """Return the panel width at a given level (excluding darts)
           * Level is counted from the top of the panel
        
        NOTE: for fitted bodice, the request is only valid for values between 0 and bust_level
        """
        # NOTE: this evaluation assumes that the top edge width is the same as bodice shoulder width 
        side_edge = self.interfaces['outside'].edges[-1]

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
    def __init__(self, design, tag='') -> None:
        """Base bottoms initialization
        """
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')
        
        self.design = design
        
        # Set of interfaces that need to be implemented
        self.interfaces = {
            'top': object()
        }
        
class StackableSkirtComponent(BaseBottoms):
    """
        Abstract definition of a skirt that can be stacked with other stackable skirts
        (connecting bottom to another StackableSkirtComponent())
    """

    def __init__(self, body, design, tag='', length=None, rise=None, slit=True, top_ruffles=True) -> None:
        """Skirt initialization

            Extra parameters (length, sleets, top_ruffles) 
            can be used to overwrite parameters in design dictionary
        """
        # BaseBottoms only accepts design and tag, not body or rise
        super().__init__(design, tag)
        
        # Store body and other parameters as instance variables
        self.body = body
        self.rise = rise
        self.slit = slit
        self.top_ruffles = top_ruffles

        # Set of interfaces that need to be implemented
        self.interfaces = {
            'top': object(),
            'bottom_f': object(),
            'bottom_b': object(),
            'bottom': object()
        }


class BaseBand(pyg.Component):
    def __init__(self, body, design, tag='', rise=None) -> None:
        """Base band initialization
        """
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')
        self.body = body
        self.design = design
        self.rise = rise
        
        # Set of interfaces that need to be implemented
        self.interfaces = {
            'top': object(),
            'bottom': object()
        }

    def length(self):
        """Base length == Length of a first panel"""
        return self._get_subcomponents()[0].length()