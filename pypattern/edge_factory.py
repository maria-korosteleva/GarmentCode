
import numpy as np
from numpy.linalg import norm

# Custom
from .edge import EdgeSequence, LogicalEdge
from ._generic_utils import vector_angle
from .interface import Interface

class EdgeSeqFactory:
    """Create EdgeSequence objects for some common edge seqeunce patterns
    """

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
        
        return EdgeSeqFactory.from_verts(*verts)

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

        edges = EdgeSeqFactory.from_verts(*verts)

        return edges

    #DRAFT
    @staticmethod
    def side_with_dart(start=(0,0), end=(1,0), width=5, depth=10, dart_position=0, right=True, panel=None):
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

        dart_shape = EdgeSeqFactory.from_verts([0, 0], [width / 2, depth], [width, 0])

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
        dart_st_point = _rel_to_abs_coords(start, end, dart_st_point)

        # Collect all together
        if right:
            dart_shape.reverse()
        dart_shape.snap_to(dart_st_point)
        dart_shape.insert(0, LogicalEdge(start, dart_shape[0].start))
        dart_shape.append(LogicalEdge(dart_shape[-1].end, end))

        # prepare the interfaces to conveniently create stitches for a dart and non-dart edges
        dart_stitch = None if panel is None else (Interface(panel, dart_shape[1]), Interface(panel, dart_shape[2]))
        
        out_interface = EdgeSequence(dart_shape[0], dart_shape[-1]) 
        out_interface = out_interface if panel is None else Interface(panel, out_interface)

        return dart_shape, dart_shape[1:-1], out_interface, dart_stitch

# Utils
def _rel_to_abs_coords(start, end, vrel):
        """Convert coordinates specified relative to vector v2 - v1 to world coords"""
        start, end, vrel = np.asarray(start), np.asarray(end), np.asarray(vrel)
        vec = end - start
        vec = vec / norm(vec)
        vec_perp = np.array([-vec[1], vec[0]])
        
        new_start = start + vrel[0] * vec
        new_point = new_start + vrel[1] * vec_perp

        return new_point 