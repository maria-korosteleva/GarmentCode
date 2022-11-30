import numpy as np
from numpy.linalg import norm
from bisect import bisect_left
from ._generic_utils import KeyWrapper

# Custom
from .base import BaseComponent
from .connector import EdgeInterfaceInstance

# DRAFT 
class GeometricEdge():
    """Class that hold elementary edges that correspond to one section between any two vertices
    """

    def __init__(self, start=(0,0), end=(0,0), parent_edge_shifts=(0, 0)) -> None:
        """
        Parameters:
            * start and end -- 2D vertex locations of the edge
            * l_edge_shifts -- dist from the start of the parent edge to the start vertex, and 
                    from the end of the parent edge to the end vertex
                    # TODO Naming??
        """

        # TODO add curvatures

        self.start = start  # NOTE: careful with references to vertex objects
        self.end = end
        self.nstart = np.array(start)
        self.nend = np.array(end)
        self.length = norm(self.nend - self.nstart)   # not if there are curvatures though!

        self.before_space = parent_edge_shifts[0]
        self.after_space = parent_edge_shifts[0]

    # Actions
    def flip(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start
        self.before_space, self.after_space = self.after_space, self.before_space

        # TODO flip curvatures

    def isVertexOnEdge(self, loc):
        """Check if vertex belongs to a straight line representation of an edge. Assuming 1D vertex 
        
        The check disregards the curvatures
        """
        return loc > self.before_space & loc < (self.before_space + self.length)



class LogicalEdge(BaseComponent):
    """Edge -- an individual segement of a panel border connecting two panel vertices, 
    where the sharp change of direction occures, the basic building block of panels

    Edges are defined on 2D coordinate system with Start vertex as an origin and (End-Start) as Ox axis

    Logical edges may be constructred from multiple geometric edges (e.g., if an edge is cut with a dart), 
    and contain internal vertices at assembly time, and be defined as smooth curves.
    
    """

    def __init__(self, start=(0,0), end=(0,0)) -> None:
        super().__init__('edge')

        
        # TODO add parameters
        # TODO add documentation

        self.start = start  # NOTE: careful with references to vertex objects
        self.end = end
        self.nstart = np.array(start)
        self.nend = np.array(end)
        self.length = norm(self.nend - self.nstart)  # TODO or dynamically -- as sum of geometric edges?

        self.geometric_edges = [GeometricEdge(self.start, self.end, (0, 0))]

        self.in_between_verts = [(self.start, 0), (self.end, self.length)]  # DRAFT
        self.geometric_ids = [0]  # DRAFT

        # Describes the possible options to connect this logical edge with other edges
        # DRAFT
        self.interfaces = [EdgeInterfaceInstance([0])] 

    # Info
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
    
    def elem_edge_len(self, v1_id, v2_id):
        """Length of an elementary edge between given vertices"""

    # Actions
    def flip(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start
        for subedge in self.geometric_edges:
            subedge.flip()

    def add_segment(self, insert_from, for_len, tol=1e-4):
        """Add vertices along the edge, creating new geometrical edges

            This is sometimes needed for connecting only portion of the edge
        """
        self.add_vertex_at_loc(insert_from)
        self.add_vertex_at_loc(insert_from + for_len)

    def add_vertex_at_loc(self, loc):
        
        # TODO would it be easier to do on definition of the Logical Edge? 
        # On projection we might need to insert these things automatically in post-processing anyway
        # (or not??)
        # might also be useful when adding darts
        # Insert by location is easier though
        # OR allow both options

        new_v = self.nstart + (loc / self.length) * (self.nend - self.nstart)

        # TODO what if vertex matches existing vertices?

        for id, edge in enumerate(self.geometric_edges):
            if edge.isVertexOnEdge(loc):
                break
        else:
            raise ValueError(f'{self.__class__.__name__}::Error::trying to insert a vertex outside of an edge')
        
        # Break the edge into two
        old_edge = self.geometric_edges[id]
        sub_1 = GeometricEdge(old_edge.start, new_v, (old_edge.before_space, 0))
        sub_1.after_space = old_edge.after_space + (old_edge.length - sub_1.length)

        sub_2 = GeometricEdge(new_v, old_edge.end, (0, old_edge.after_space))
        sub_2.before_space = old_edge.before_space + sub_1.length

        # Insert them into the list
        self.geometric_edges.pop(id)
        self.geometric_edges.insert(id, sub_2)
        self.geometric_edges.insert(id, sub_1)

        # TODO Break down the edge interfaces that involve the two elements?
        for id, intf in enumerate(self.interfaces):
            # Check if belongs
            # Subdivide and insert
            pass

        
        # DRAFT
        id = bisect_left(KeyWrapper(self.in_between_verts, key=lambda c: c[1]), loc)
        self.in_between_verts.insert((new_v, loc))

        return id
        
    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges"""

        # TODO return full panel definition -- LogicalEdges might produce stitches as well!
        return [self.start, self.end], [{"endpoints": [0, 1]}]