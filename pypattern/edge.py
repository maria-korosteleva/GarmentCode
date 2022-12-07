from copy import deepcopy, copy
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

    def __init__(self, start=[0,0], end=[0,0]) -> None:
        """ Simple edge inititalization.
        Parameters: 
            * start, end: from/to vertcies that the edge connectes, describing the _interface_ of an edge
            * ruffle_rate: elongate the edge at assembly time by this rate. This parameter creates ruffles on stitches

            # TODO Add support for fold schemes to allow guided folds at the edge (e.g. pleats)
        """
        super().__init__('edge')

        # TODO add curvatures
        # TODO add parameters
        # TODO add documentation

        self.start = start  # NOTE: careful with references to vertex objects
        self.end = end

        # ID w.r.t. other edges in a super-panel
        # Filled out at the panel assembly time
        self.geometric_id = 0

    def length(self):
        """Return current length of an edge.
            Since vertices may change their locations externally, the length is dynamically evaluated
        """
        self.length = norm(np.asarray(self.end) - np.asarray(self.start))

    def __eq__(self, __o: object) -> bool:
        """Special implementation of comparison: same edges == edges are allowed to be connected
            Edges are the same if their interface representation (no ruffles) is the same up to rigid transformation (rotation/translation)
                => vertices do not have to be on the same locations
        """
        if not isinstance(__o, LogicalEdge):
            return False

        # Base length is the same
        if self.length() != __o.length():
            return False
            
        # TODO Curvature is the same
        # TODO special features are matching 

        # TODO Mapping geometric ids to vertices pairs??
        # I need a method to get geometric ids \ for a given subsection of the edge
        # Actually.. Edge interface definitions????

        return True

    def __str__(self) -> str:
        return f'[{self.start[0]:.2f}, {self.start[1]:.2f}] -> [{self.end[0]:.2f}, {self.end[1]:.2f}]'  # TODO account for curvatures

    def __repr__(self) -> str:
        """ 'Official string representation' -- for nice printing of lists of edges
        
        https://stackoverflow.com/questions/3558474/how-to-apply-str-function-when-printing-a-list-of-objects-in-python
        """
        return self.__str__()

    # Actions
    def flip(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start

        # TODO flip curvatures
        
    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges"""

        # TODO simply use the edge sequence? Without defining the vertices??
        return [self.start, self.end], {"endpoints": [0, 1]}


class EdgeSequence():
    """Represents a sequence of (chained) edges (e.g. every next edge starts from the same vertex that the previous edge ends with
        and allows building some typical edge sequences
    """
    def __init__(self, *args) -> None:
        self.edges = []
        for arg in args:
            self.append(arg)

    # ANCHOR Properties
    def __getitem__(self, i):
        return self.edges[i]

    def __len__(self):
        return len(self.edges)

    def __str__(self) -> str:
        return str(self.edges)
    
    def __repr__(self) -> str:
        return self.__str__()

    def isLoop(self):
        return self.edges[0].start is self.edges[-1].end and len(self) > 1

    def isChained(self):
        """Does the sequence of edges represent correct chain?"""
        if len(self) < 2:
            return False

        for i in range(1, len(self.edges)):
            if self.edges[i].start is not self.edges[i-1].end:
                # This should be helpful to catch bugs
                print(f'{self.__class__.__name__}::Warning!::Edge sequence is not properly chained')
                return False
        return True

    # ANCHOR Modifiers
    # All modifiers return self object to allow chaining
    def append(self, item):
        if isinstance(item, LogicalEdge):
            self.edges.append(item)
            # TODO check if chained right away!
        elif isinstance(item, list):  # Assuming list of LogicalEdge objects
            self.edges += item
        elif isinstance(item, EdgeSequence):
            self.edges += item.edges
        else:
            raise ValueError(f'{self.__class__.__name__}::Error::Trying to add object of incompatible type {type(item)}')
        return self

    def insert(self, i, item):
        if isinstance(item, LogicalEdge):
            self.edges.insert(i, item)
        elif isinstance(item, list) or isinstance(item, EdgeSequence):
            for j in range(len(item)):
                self.edges.insert(i + j, item[j])
        else:
            raise NotImplementedError(f'{self.__class__.__name__}::Error::incerting object of {type(item)} not suported (yet)')
        return self
    
    def pop(self, i):
        self.edges.pop(i)
        return self

    def reverse(self):
        """Reverse edge sequence in-place"""
        self.edges.reverse()
        for edge in self.edges:
            edge.flip()
        return self

    def snap_to(self, new_origin=[0, 0]):
        """Translate the edge seq vertices s.t. the first vertex is at new_origin
        """
        start = copy(self[0].start)
        shift = [new_origin[0] - start[0], new_origin[1] - start[1]]
        for edge in self:
            edge.end[0] += shift[0]
            edge.end[1] += shift[1]

        self[0].start[0] += shift[0]
        self[0].start[1] += shift[1]

        return self


    # ANCHOR Factories for some tipical edge sequences
    def copy(self):
        """Create a copy of a current edge sequence preserving the chaining property of edge sequences"""
        new_seq = deepcopy(self)

        # deepcopy recreates the vertex objects on both sides of the edges
        # in chaned edges those vertex objects are supposed to be shared
        # by neighbor edges

        # fix vertex sharing
        for i in range(1, len(new_seq)):
            new_seq[i].start = new_seq[i-1].end
            
        if self.isLoop():
            new_seq[-1].end = new_seq[0].start

        return new_seq

    @staticmethod
    def from_verts(*verts, loop=False):
        """Generate edge sequence from given vertices. If loop==True, the method also closes the edge sequence as a loop
        """
        # TODO Curvatures
        seq = EdgeSequence(LogicalEdge(verts[0], verts[1]))
        for i in range(2, len(verts)):
            seq.append(LogicalEdge(seq[-1].end, verts[i]))

        if loop:
            seq.append(LogicalEdge(seq[-1].end, seq[0].start))
        
        seq.isChained()
        return seq

    @staticmethod
    def side_with_cut(start=(0,0), end=(1,0), start_cut=0, end_cut=0):
        """ Edge with internal vertices that allows to stitch only part of the border represented
            by the long side edge

            start_cut and end_cut specify the fraction of the edge to to add extra vertices at
        """
        # TODO Curvature support?

        nstart, nend = np.array(start), np.array(end)
        verts = [start]

        if start_cut > 0:
            verts.append((start + start_cut * (nend-nstart)).tolist())
        if end_cut > 0:
            verts.append((end - end_cut * (nend-nstart)).tolist())
        verts.append(end)

        edges = EdgeSequence.from_verts(*verts)

        return edges

