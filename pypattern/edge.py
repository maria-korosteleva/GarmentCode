from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm

# Custom
from .base import BaseComponent
from ._generic_utils import vector_angle

# TODO rename 
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
        return norm(np.asarray(self.end) - np.asarray(self.start))

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
    # TODO 2D rotation of edge sequences
    # TODO Scaling of edge sequences
    """Represents a sequence of (chained) edges (e.g. every next edge starts from the same vertex that the previous edge ends with
        and allows building some typical edge sequences
    """
    def __init__(self, *args) -> None:
        self.edges = []
        for arg in args:
            self.append(arg)

    # ANCHOR Properties
    def __getitem__(self, i):
        if isinstance(i, slice):
            # return an EdgeSequence object for slices
            e_slice = self.edges[i]
            return EdgeSequence(e_slice)
        else:
            return self.edges[i]

    def index(self, elem):
        return self.edges.index(elem)

    def __len__(self):
        return len(self.edges)

    def __contains__(self, item):
        # check presence by comparing references
        return any([item is e for e in self.edges])

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

    def fractions(self):
        """Fractions of the lengths of each edge in sequence w.r.t. 
            the whole sequence
        """
        total_len = sum([e.length() for e in self.edges])

        return [e.length() / total_len for e in self.edges]

    # ANCHOR Modifiers
    # All modifiers return self object to allow chaining
    # Wrappers around python's list
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

    def substitute(self, orig, new):
        """Remove orign item from the list and place seq into it's place
            orig can be either an id of an item to remove 
            or an instance of LogicalEdge that exists in the current sequence
        """
        if isinstance(orig, LogicalEdge):
            orig = self.index(orig)
        self.pop(orig)
        self.insert(orig, new)
        return self

    def reverse(self):
        """Reverse edge sequence in-place"""
        self.edges.reverse()
        for edge in self.edges:
            edge.flip()
        return self

    # EdgeSequence-specific
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

    def close_loop(self):
        """if edge loop is not closed, add and edge to close it"""
        self.isChained()  # print worning if smth is wrong
        if not self.isLoop():
            self.append(LogicalEdge(self[-1].end, self[0].start))

    def rotate(self, angle):
        """Rotate edge sequence by angle in place, using first point as a reference

        Parameters: 
            angle -- desired rotation angle in radians (!)
        """
        curr_start = copy(self[0].start)
        
        # set the start point to zero
        self.snap_to([0, 0])
        rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])

        for edge in self.edges:
            edge.end[:] = np.matmul(rot, edge.end)
        
        # recover the original location
        self.snap_to(curr_start)

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

    def from_fractions(start, end, frac=[1]):
        """A sequence of edges between start and end wich lengths are distributed
            as specified in frac list 
        Parameters:
            * frac -- list of legth fractions. Every entry is in (0, 1], 
                all entries sums up to 1
        """
        # TODO fractions of curvy edges?
        frac = [abs(f) for f in frac]
        if abs(sum(frac) - 1) > 1e-4:
            raise RuntimeError(f'EdgeSequence::Error::fraction list does not follow the requirements')

        vec = np.asarray(end) - np.asarray(start)
        verts = [start]
        for i in range(len(frac) - 1):
            verts.append(
                [verts[-1][0] + frac[i]*vec[0],
                verts[-1][1] + frac[i]*vec[1]]
            )
        verts.append(end)
        
        return EdgeSequence.from_verts(*verts)

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

    #DRAFT
    @staticmethod
    def side_with_dart(start=(0,0), end=(1,0), width=5, depth=10, dart_position=0, right=True):
        """Create a seqence of edges that represent a side with a dart with given parameters
        Parameters:
            * start and end -- vertices between which side with a dart is located
            * width -- width of a dart opening
            * depth -- depth of a dart (distance between the opening and the farthest vertex)
            * dart_position -- position along the edge (to the beginning of the dart)
            * right -- whether the dart is created on the right from the edge direction (otherwise created on the left). Default - Right (True)

        Returns: 
            * Full edge with a dart
            * References to dart edges
            * References to non-dart edges

        NOTE: Darts always have the same length on the sides
        """
        # TODO Curvatures?? -- on edges, dart sides
        # TODO Non-straight darts? They won't have the sides of the same length, so it makes things complicated..

        # TODO The side edge need to be angled s.t. the sewed thing is straight (original edge)..
        # TODO Target edge length / shapes as input
        # TODO Multiple darts on one side (can we make this fucntions re-usable/chainable?)

        dart_shape = EdgeSequence.from_verts([0, 0], [width / 2, depth], [width, 0])

        # Align with the direction between vertices
        angle = vector_angle(
            np.array(end) - np.array(start),
            np.array(dart_shape[0].start) - np.array(dart_shape[-1].end))
        angle *= -1 if right else 1  # account for a desired orientation of the cut
        dart_shape.rotate(angle)
        
        # TODO support positions other then in the middle between vertices

        # Create new vertex that the dart will start from
        d_to_center = norm(np.array(end) - np.array(start))
        # coords relative to start vertex
        dart_st_point = [(d_to_center - width) / 2, 0]
        dart_st_point[1] = dart_st_point[0] * width / 2 / depth
        # absolute position
        dart_st_point = EdgeSequence._rel_to_abs_coords(start, end, dart_st_point)

        # Collect all together
        if right:
            dart_shape.reverse()
        dart_shape.snap_to(dart_st_point)
        dart_shape.insert(0, LogicalEdge(start, dart_shape[0].start))
        dart_shape.append(LogicalEdge(dart_shape[-1].end, end))

        return dart_shape, dart_shape[1:-1], EdgeSequence(dart_shape[0], dart_shape[-1])

    @staticmethod
    def _rel_to_abs_coords(start, end, vrel):
        """Convert coordinates specified relative to vector v2 - v1 to world coords"""
        start, end, vrel = np.asarray(start), np.asarray(end), np.asarray(vrel)
        vec = end - start
        vec = vec / norm(vec)
        vec_perp = np.array([-vec[1], vec[0]])
        
        new_start = start + vrel[0] * vec
        new_point = new_start + vrel[1] * vec_perp

        return new_point 
