import numpy as np
from numpy.linalg import norm

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

        self.start = start  # NOTE: careful with references to vertex objects
        self.end = end
        self.nstart = np.array(start)
        self.nend = np.array(end)
        self.length = norm(self.nend - self.nstart)
        self.in_between_verts = [(self.start, 0), (self.end, self.length)]
        self.geometric_ids = []

        # Describes the possible options to connect this logical edge with other edges
        # TODO implement
        self.interfaces = [] 

    def __eq__(self, __o: object) -> bool:
        """Special implementation of comparison
            Edges are the same up to rigid transformation (rotation/translation)
                => vertices do not have to be on the same locations
        """
        if not isinstance(__o, LogicalEdge):
            return False

        # Base length is the same
        if self.length != __o.length:
            return False
            
        # TODO Curvature is the same
        # TODO special features are matching 

        # TODO Mapping geometric ids to vertices pairs??
        # I need a method to get geometric ids \ for a given subsection of the edge
        # Actually.. Edge interface definitions????

        return True

    # Actions
    def flip(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start

        # TODO flip curvatures
        

    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges"""

        # TODO simply use the edge sequence? Without defining the vertices??
        return [self.start, self.end], [{"endpoints": [0, 1]}]