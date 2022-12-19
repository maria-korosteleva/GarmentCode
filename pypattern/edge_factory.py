
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
    def side_with_dart(start=(0,0), end=(100,0), width=5, depth=10, dart_position=50, opening_angle=180, right=True, modify='both', panel=None):
        """Create a seqence of edges that represent a side with a dart with given parameters
        Parameters:
            * start and end -- vertices between which side with a dart is located
            * width -- width of a dart opening
            * depth -- depth of a dart (distance between the opening and the farthest vertex)
            * dart_position -- position along the edge (from the start vertex)
            * opening angle (deg) -- angle between side edges after the dart is stitched (as evaluated opposite from the dart). default = 180 (straight line)
            * right -- whether the dart is created on the right from the edge direction (otherwise created on the left). Default - Right (True)
            * modify -- which vertex position to update to accomodate for contraints: 'start', 'end', or 'both'. Default: 'both'

        Returns: 
            * Full edge with a dart
            * References to dart edges
            * References to non-dart edges
            * Suggested dart stitch

        NOTE: (!!) the end of the edge might shift to accomodate the constraints
        NOTE: The routine makes sure that the the edge is straight after the dart is stitched
        NOTE: Darts always have the same length on the sides
        """
        # TODO Curvatures?? -- on edges, dart sides

        # TODO Multiple darts on one side (can we make this fucntions re-usable/chainable?)

        # TODO One of the end locations is modified. how will it affect other edges?
        # TODO opening angle

        # Targets
        v0, v1 = np.asarray(start), np.asarray(end)
        L = norm(v1 - v0)
        d0, d1 = dart_position, L - dart_position
        depth_perp = np.sqrt((depth**2 - (width / 2)**2))
        dart_side = depth

        # Extended triangle -- sides
        delta_l = dart_side * width / (2 * depth_perp)  # extention of edge length beyong the dart points
        side0, side1 = d0 + delta_l, d1 + delta_l
        
        # long side (connects original vertices)
        alpha = abs(np.arctan(width / 2 / depth_perp))  # half of dart tip angle
        top_angle = np.pi - 2*alpha  # top of the triangle (v0, imaginative dart top, v1)
        long_side = np.sqrt(side0**2 + side1**2 - 2*side0*side1*np.cos(top_angle))
        
        # angles of extended triangle
        sin0, sin1 = side1 * np.sin(top_angle) / long_side, side0 * np.sin(top_angle) / long_side
        angle0, angle1 = np.arcsin(sin0), np.arcsin(sin1)

        # Find the location of dart points: start of dart cut
        p1x = d0 * np.cos(angle0)
        p1y = d0 * sin0
        p1 = np.array([p1x, p1y])

        p1 = _rel_to_abs_coords(v0, v1, p1)

        # end of dart cut
        p2x = long_side - (d1 * np.cos(angle1))
        p2y = d1 * sin1
        p2 = np.array([p2x, p2y])
        p2 = _rel_to_abs_coords(v0, v1, p2)

        # Tip of the dart
        p_vec = p2 - p1
        p_perp = np.array([-p_vec[1], p_vec[0]])
        p_perp = p_perp / norm(p_perp) * depth_perp

        p_tip = p1 + p_vec / 2 - p_perp

        # New location of the dart end to satisfy the requested length
        new_end = _rel_to_abs_coords(v0, v1, np.array([long_side, 0]))
        shift = new_end - v1
        end[:] = _rel_to_abs_coords(v0, v1, np.array([long_side, 0]))

        # Gather all together
        # TODO After adjustments?
        dart_shape = EdgeSeqFactory.from_verts(p1.tolist(), p_tip.tolist(), p2.tolist())
        if not right:
            # flip dart to be the left of the vector
            dart_shape.reflect(start, end)

        dart_shape.insert(0, LogicalEdge(start, dart_shape[0].start))
        dart_shape.append(LogicalEdge(dart_shape[-1].end, end))

        # re-distribute the changes & adjust the opening angle as requested
        angle_diff = np.deg2rad(180 - opening_angle)
        if modify == 'both':
            dart_shape.translate_by(-shift / 2)
            # TODO check direction
            dart_shape[0].reverse().rotate(-angle_diff / 2).reverse()
            dart_shape[-1].rotate(angle_diff / 2)
        elif modify == 'end':
            # Align the beginning of the dart with original direction
            dart_shape.rotate(vector_angle(p1-v0, v1-v0))
            dart_shape[-1].rotate(angle_diff)  # TODO check direction
        elif modify == 'start':
            # Align the end of the dart with original direction & shift the change onto the start vertex
            dart_shape.translate_by(-shift)
            dart_shape.reverse()  # making the end vertex the start (to rotate around)
            dart_shape.rotate(vector_angle(p2-new_end, -(v1-v0)))
            dart_shape[-1].rotate(-angle_diff)    # TODO check direction
            dart_shape.reverse()  # original order

        # DEBUG
        print(f'Fin side length: {dart_shape[0].length() + dart_shape[-1].length()}')
        print(f'Fin tri length: {long_side}')

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