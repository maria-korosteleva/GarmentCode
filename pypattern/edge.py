
# Custom
from .base import BaseComponent

class LogicalEdge(BaseComponent):
    """Edge -- an individual segement of a panel border connecting two panel vertices, 
    where the sharp change of direction occures, the basic building block of panels

    Edges are defined on 2D coordinate system with Start vertex as an origin and (End-Start) as Ox axis

    Logical edges may be constructred from multiple geometric edges (e.g., if an edge is cut with a dart), 
    and contain internal vertices at assembly time, and be defined as smooth curves.
    
    """

    def __init__(self, start=(0,0), end=(0,0)) -> None:
        super().__init__('edge')

        # TODO add curvatures
        # TODO add parameters
        # TODO add documentation

        self.start = start
        self.end = end
        self.geometric_ids = []

    def flip(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start

        # TODO flip curvatures

    def assembly(self):
        """Returns the dict-based representation of edges"""

        # TODO simply use the edge sequence? Without defining the vertices??
        return [self.start, self.end], [{"endpoints": [0, 1]}]


# DRAFT for the connectivity shapes
class ConnectorEdge():
    """Edge that describes connecting interface of a component. 
        
        Differs from the generic edge by describing how it relates to the geometric edge of a panel

        Component interfaces do not necessarily have to follow the shape of panel edges, 
        which allows to create flounces, pleats and partial connections

    """

    def __init__(self, connector_shape: LogicalEdge, parent_edge: LogicalEdge) -> None:
        """ Create connector edge
        Parameters:
            * connector_edge: describes the shape of the interface edge 
            * parent_edge: the geometric edge of the panel that connector attaches too
        """
        # TODO Connector shorter than parent -- connection location
        # TODO Connector follows the parent length with different shape
        # TODO what space is connector defined in?
        self.edge = connector_shape
        self.parent = parent_edge

    def connect_to(self, connector):
        """Connect current connector with connector of another panel"""

        # TODO there is probably a more abstract object that should do it
        self.connecting = connector
        connector.connect_to(self)
