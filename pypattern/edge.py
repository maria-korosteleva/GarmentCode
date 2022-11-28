import numpy as np

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

    def length(self) -> float:
        # as a function in case start/end changes through the life of an object
        return np.linalg.norm(np.array(self.end) - np.array(self.start))

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, LogicalEdge):
            return False

        # Base length is the same
        if self.length() != __o.length():
            return False
            
        # TODO Curvature is the same
        # TODO special features are matching 

        return True
