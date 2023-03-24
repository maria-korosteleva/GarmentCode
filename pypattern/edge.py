from copy import deepcopy, copy
import numpy as np
from numpy.linalg import norm

# Custom
from .generic_utils import R2D

class Edge():
    """Edge -- an individual segement of a panel border connecting two panel vertices, 
     the basic building block of panels

    Edges are defined on 2D coordinate system with Start vertex as an origin and (End-Start) as Ox axis
    """

    def __init__(self, start=[0,0], end=[0,0]) -> None:
        """ Simple edge inititalization.
        Parameters: 
            * start, end: from/to vertcies that the edge connectes, describing the _interface_ of an edge

            # TODO Add support for fold schemes to allow guided folds at the edge (e.g. pleats)
        """
        # TODO add curvatures

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
        if not isinstance(__o, Edge):
            return False

        # Base length is the same
        if self.length() != __o.length():
            return False
            
        # TODO Curvature is the same

        return True

    def __str__(self) -> str:
        return f'[{self.start[0]:.2f}, {self.start[1]:.2f}] -> [{self.end[0]:.2f}, {self.end[1]:.2f}]'  # TODO account for curvatures

    def __repr__(self) -> str:
        """ 'Official string representation' -- for nice printing of lists of edges
        
        https://stackoverflow.com/questions/3558474/how-to-apply-str-function-when-printing-a-list-of-objects-in-python
        """
        return self.__str__()

    def midpoint(self):
        """Center of the edge"""
        return (np.array(self.start) + np.array(self.end)) / 2

    # Actions
    def reverse(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start

        # TODO flip curvatures
        return self
    
    def snap_to(self, new_start=[0, 0]):
        """Translate the edge vertices s.t. the start is at new_start
        """
        self.end[0] = self.end[0] - self.start[0] + new_start[0]
        self.end[1] = self.end[1] - self.start[1] + new_start[1]

        self.start[:] = new_start
        return self

    def rotate(self, angle):
        """Rotate edge by angle in place, using first point as a reference

        Parameters: 
            angle -- desired rotation angle in radians (!)
        """
        curr_start = copy(self.start)
        
        # set the start point to zero
        self.snap_to([0, 0])
        self.end[:] = np.matmul(R2D(angle), self.end)
        
        # recover the original location
        self.snap_to(curr_start)

        return self
        
    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges, 
            compatible with core -> BasePattern JSON (dict) 
        """

        return [self.start, self.end], {"endpoints": [0, 1]}


class CircleEdge(Edge):
    """Curvy edge as circular arc"""

    def __init__(self, start=[0, 0], end=[0, 0], radius=0, large_arc=False, right=True) -> None:
        super().__init__(start, end)

        # TODO Specify by arc (length) (simplify interface?)
        # TODO Func parameters description https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists
        # TODO check full circle
        # TODO Propagate to sub-functions and operators 
        # FIXME Autonorm is going crasy with the circular edges

        self.radius = radius
        self.right = right
        self.large_arc = large_arc

        arc_len = norm(np.asarray(self.end) - np.asarray(self.start))
        self.arc = 2 * np.arcsin(arc_len / self.radius / 2)

    def assembly(self):
        """Returns the dict-based representation of edges, 
            compatible with core -> BasePattern JSON (dict) 
        """

        # TODO Try the 3-point representation? Might be more compact + more continious
        # How much human readible this one should be?
        # Even one number (Y axis) could be enough 

        return (
            [self.start, self.end], 
            {
                "endpoints": [0, 1], 
                "curvature": {
                    "type": 'circle',
                    "params": [self.radius, self.large_arc, self.right]
                }
            })

# TODO Curvy edges
# TODO Remove old version??

class EdgeSequence():
    """Represents a sequence of (possibly chained) edges (e.g. every next edge starts from the same vertex that the previous edge ends with
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
        # Find the same object (by reference) 
        # list.index() is doing something different..
        # https://stackoverflow.com/a/47057419
        return next(i for i, e in enumerate(self.edges) if elem is e)

    def __len__(self):
        """Number of edges in the sequence"""
        return len(self.edges)

    def __contains__(self, item):
        # check presence by comparing references
        return any([item is e for e in self.edges])

    def __str__(self) -> str:
        return 'EdgeSeq: ' + str(self.edges)
    
    def __repr__(self) -> str:
        return self.__str__()

    def length(self):
        """Total length of edges"""
        return sum([e.length() for e in self.edges])

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

    def fractions(self) -> list:
        """Fractions of the lengths of each edge in sequence w.r.t. 
            the whole sequence
        """
        total_len = sum([e.length() for e in self.edges])

        return [e.length() / total_len for e in self.edges]

    def lengths(self) -> list:
        """Lengths of individual edges in the sequence"""
        return [e.length() for e in self.edges]

    def verts(self):
        """Return all vertex objects"""
        verts = [self.edges[0].start]
        for e in self.edges:
            if e.start is not verts[-1]:  # avoid adding the vertices of chained edges twice
                verts.append(e.start)
            verts.append(e.end)
        if verts[0] is verts[-1]:  # don't double count the loop origin
            verts.pop(-1)
        return verts

    # ANCHOR Modifiers
    # All modifiers return self object to allow chaining
    # Wrappers around python's list
    def append(self, item):
        if isinstance(item, Edge):
            self.edges.append(item)
        elif isinstance(item, list):  # List of edge / EdgeSeq objects
            for e in item:
                self.append(e)
        elif isinstance(item, EdgeSequence):
            self.edges += item.edges
        else:
            raise ValueError(f'{self.__class__.__name__}::Error::Trying to add object of incompatible type {type(item)}')
        return self

    def insert(self, i, item):
        if isinstance(item, Edge):
            self.edges.insert(i, item)
        elif isinstance(item, list) or isinstance(item, EdgeSequence):
            for j in range(len(item)):
                self.edges.insert(i + j, item[j])
        else:
            raise NotImplementedError(f'{self.__class__.__name__}::Error::incerting object of {type(item)} not suported (yet)')
        return self
    
    def pop(self, i):
        if isinstance(i, Edge):
            i = self.index(i)
        self.edges.pop(i)
        return self

    def substitute(self, orig, new):
        """Remove orign item from the list and place seq into it's place
            orig can be either an id of an item to remove 
            or an instance of Edge that exists in the current sequence
        """
        if isinstance(orig, Edge):
            orig = self.index(orig)
        self.pop(orig)
        self.insert(orig, new)
        return self

    def reverse(self):
        """Reverse edge sequence in-place"""
        self.edges.reverse()
        for edge in self.edges:
            edge.reverse()
        return self

    # EdgeSequence-specific
    def translate_by(self, shift):
        """Translate the edge seq vertices s.t. the first vertex is at new_origin
        """
        for v in self.verts():
            v[0] += shift[0]
            v[1] += shift[1]
        return self

    def snap_to(self, new_origin=[0, 0]):
        """Translate the edge seq vertices s.t. the first vertex is at new_origin
        """
        start = copy(self[0].start)
        shift = [new_origin[0] - start[0], new_origin[1] - start[1]]
        self.translate_by(shift)

        return self

    def close_loop(self):
        """if edge loop is not closed, add and edge to close it"""
        self.isChained()  # print worning if smth is wrong
        if not self.isLoop():
            self.append(Edge(self[-1].end, self[0].start))

    def rotate(self, angle):
        """Rotate edge sequence by angle in place, using first point as a reference

        Parameters: 
            angle -- desired rotation angle in radians (!)
        """
        curr_start = copy(self[0].start)
        
        # set the start point to zero
        self.snap_to([0, 0])
        rot = R2D(angle)

        for v in self.verts():
            v[:] = np.matmul(rot, v)
        
        # recover the original location
        self.snap_to(curr_start)

        return self

    def extend(self, factor):
        """Extend or shrink the edges along the line from start of the first edge to the 
        end of the last edge in sequence
        """
        # TODO Version With preservation of total length?

        # Need to take the target line from the chained order
        if not self.isChained():  
            chained_edges = self.chained_order()
            chained_edges.isChained()
            if chained_edges.isLoop():
                print(f'{self.__class__.__name__}::Warning::Extending looped edge sequences is not available')
                return self
        else: 
            chained_edges = self
        
        target_line = np.array(chained_edges[-1].end) - np.array(chained_edges[0].start)
        target_line = target_line / norm(target_line)

        # gather vertices
        verts_coords = self.verts()
        nverts_coords = np.array(verts_coords)
        
        # adjust their position based on projection to the target line
        verts_projection = np.empty(nverts_coords.shape)
        fixed = nverts_coords[0]
        for i in range(nverts_coords.shape[0]):
            verts_projection[i] = (nverts_coords[i] - fixed).dot(target_line) * target_line

        new_verts = verts_coords - (1 - factor) * verts_projection

        # Update vertex objects
        for i in range(len(verts_coords)):
            verts_coords[i][:] = new_verts[i]

        return self

    def reflect(self, v0, v1):
        """Reflect 2D points w.r.t. 1D line defined by two points"""
        v0, v1 = np.asarray(v0), np.asarray(v1)
        vec = np.asarray(v1) - np.asarray(v0)
        vec = vec / norm(vec)  # normalize

        # https://demonstrations.wolfram.com/ReflectionMatrixIn2D/#more
        Ref = np.array([
            [ 1 - 2 * vec[1]**2,  2*vec[0]*vec[1]],
            [ 2*vec[0]*vec[1],    - 1 + 2 * vec[1]**2 ]
            ])
        
        # translate -> reflect -> translate back
        for v in self.verts():
            v[:] = np.matmul(Ref, np.asarray(v) - v0) + v0

        return self

    # ANCHOR New sequences & versions
    def copy(self):
        """Create a copy of a current edge sequence preserving the chaining property of edge sequences"""
        new_seq = deepcopy(self)

        # deepcopy recreates the vertex objects on both sides of the edges
        # in chaned edges those vertex objects are supposed to be shared
        # by neighbor edges

        for i in range(1, len(new_seq)):
            if self[i].start is self[i-1].end:
                new_seq[i].start = new_seq[i-1].end
            
        if self.isLoop():
            new_seq[-1].end = new_seq[0].start

        return new_seq

    def chained_order(self):
        """ Attempt to restore a chain in the EdgeSequence
            The chained edge sequence may loose it's property if the edges were reveresed externally. 
            This routine created a copy of the currect sequence with aligned the order of edges,

            It might be useful for various calculations
        
        """
        chained = self.copy()
        
        for i in range(len(chained)):
            # Assuming the previous one is already sorted
            if i > 0 and chained[i].end is chained[i-1].end:
                chained[i].reverse()
            # Not connected to the previous one
            elif (i + 1 < len(chained)
                    and (chained[i].start is chained[i+1].start or chained[i].start is chained[i+1].end)):
                chained[i].reverse()
            # not connected to anything or connected properly -- leave as is
        
        return chained