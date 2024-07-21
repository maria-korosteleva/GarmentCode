import pygarment as pyg

class BaseBodicePanel(pyg.Panel):
    """Base class for bodice panels that defines expected interfaces and common functions"""
    def __init__(self, name, body, design) -> None:
        super().__init__(name)
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

        return (level * x / y) + self.body['shoulder_w'] / 2


class BaseBottoms(pyg.Component):
    """A base class for all the bottom components.
        Defines common elements: 
        * List of interfaces
        * Presence of the rise value
    """
    def __init__(self, body, design, tag='', rise=None) -> None:
        """Base bottoms initialization
        """
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')
        
        self.body = body
        self.design = design
        self.rise = rise
        
        # Set of interfaces that need to be implemented
        self.interfaces = {
            'top': object()
        }
        
    def get_rise(self):
        """Return a rise value for a given component"""
        return self.rise
    
    def eval_rise(self, rise):
        """Evaluate updated hip and waist-related measurements, 
            corresponding to the provided rise value 
        """
        waist, hips = self.body['waist'], self.body['hips']
        hips_level = self.body['hips_line']
        self.adj_hips_depth = rise * hips_level
        self.adj_waist = pyg.utils.lin_interpolation(hips, waist, rise)

        self_adj_back_waist = pyg.utils.lin_interpolation(
            self.body['hip_back_width'], self.body['waist_back_width'], rise)

        return self.adj_waist, self.adj_hips_depth, self_adj_back_waist

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
        super().__init__(body, design, tag, rise=rise)
        
        pass

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