import numpy as np
from numpy.linalg import norm
from bisect import bisect_left
from ._generic_utils import KeyWrapper

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

# DRAFT edge subdivision
    def subdivide(self, insert_from, for_len):
        """Add vertices along the edge, creating new geometrical edges

            This is sometimes needed for connecting only portion of the edge
        """
        # find the 2D location of new vertices to add
        new_v_start = self.nstart + (insert_from / self.length) * (self.nend - self.nstart)
        new_v_end = new_v_start + (for_len / self.length) * (self.nend - self.nstart)

        # incert them at appropriate position in the vertex list
        self._add_vertex(new_v_start.tolist(), insert_from)
        self._add_vertex(new_v_end.tolist(), for_len)


    def _add_vertex(self, vert, loc=None):
        if loc is None:
            loc = norm(vert - self.start)
        
        id = bisect_left(KeyWrapper(self.in_between_verts, key=lambda c: c[1]), loc)
        self.in_between_verts.insert((vert, loc))

        return id
        

    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges"""

        # TODO simply use the edge sequence? Without defining the vertices??
        return [self.start, self.end], [{"endpoints": [0, 1]}]