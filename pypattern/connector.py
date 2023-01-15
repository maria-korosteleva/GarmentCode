from numpy.linalg import norm
import numpy as np

# Custom
from .edge_factory import EdgeSeqFactory
from .interface import Interface
from .generic_utils import close_enough

class StitchingRule():
    """High-level stitching instructions connecting two component interfaces
    """
    def __init__(self, int1:Interface, int2:Interface) -> None:
        """NOTE: When connecting interfaces with different edge count on both sides, 
            note that the edge sequences change their structure.
            Use of the same interfaces in other stitches (creating 3+way stitch edge) may fail. 
        """
        # TODO Explicitely support 3+way stitches
        self.int1 = int1
        self.int2 = int2

        if not self.isMatching():
            self.match_interfaces()

        if not close_enough(
                len1:=int1.projecting_edges().length(), 
                len2:=int2.projecting_edges().length(), 
                tol=0.3):   # NOTE = 3 mm
            print(
                f'{self.__class__.__name__}::Warning::Projected edges do not match in the stitch: \n'
                f'{len1}: {int1}\n{len2}: {int2}')
    

    def isMatching(self, tol=0.1):
        # if both the breakdown and relative partitioning is similar

        rev_frac1 = self.int1.edges.fractions()
        rev_frac1.reverse()

        return (len(self.int1) == len(self.int2) 
                and (np.allclose(self.int1.edges.fractions(), self.int2.edges.fractions(), atol=tol)
                    or np.allclose(rev_frac1, self.int2.edges.fractions(), atol=tol)
                )
        )


    def isTraversalMatching(self):
        """Check if the traversal direction of edge sequences matches or needs to be swapped"""

        if len(self.int1.edges) > 1:
            # Make sure the direction is matching
            # 3D distance between corner vertices
            start_1 = self.int1.panel[0].point_to_3D(self.int1.edges[0].midpoint())
            start_2 = self.int2.panel[0].point_to_3D(self.int2.edges[0].midpoint())

            end_1 = self.int1.panel[-1].point_to_3D(self.int1.edges[-1].midpoint())
            end_2 = self.int2.panel[-1].point_to_3D(self.int2.edges[-1].midpoint())
            
            stitch_dist_straight = norm(start_2 - start_1) + norm(end_2 - end_1)
            stitch_dist_reverse = norm(start_2 - end_1) + norm(end_2 - start_1)

            if stitch_dist_reverse < stitch_dist_straight:
                # We need to swap traversal direction
                return False
        return True


    def match_interfaces(self):
        """ Subdivide the interface edges on both sides s.t. they are matching 
            and can be safely connected
            (same number of edges on each side and same relative fractions)
        
            Serializable format does not natively support t-stitches, 
            so the longer edges needs to be broken down into matching segments
            # SIM specific
        """

        # Eval the fractions corresponding to every segments in the interfaces
        # Using projecting edges to match desired gather patterns
        frac1 = self.int1.projecting_edges().fractions()
        if not self.isTraversalMatching():      # match the other edge orientation before passing on
            frac1.reverse()

        frac2 = self.int2.projecting_edges().fractions()
        if not self.isTraversalMatching():      # match the other edge orientation before passing on
            frac2.reverse()   

        self._match_to_fractions(self.int1, frac2)
        self._match_to_fractions(self.int2, frac1)

    def _match_to_fractions(self, inter:Interface, to_add, tol=1e-3):
        """Add the vertices at given location to the edge sequence in a given interface

        Parameters:
            * inter -- interface to modify
            * to_add -- the faractions of segements to be projected onto the edge sequence in the inter
            * tol -- the proximity of vertices when they can be regarded as the same vertex.  
                    NOTE: tol should be shorter then the smallest expected edge
        """

        # NOTE Edge sequences to subdivide might be disconnected 
        # (even belong to different panels), so we need to subdivide per edge

        # Go over the edges keeping track of their fractions
        add_id, in_id = 0, 0
        covered_init, covered_added = 0, 0
        total_len = inter.projecting_edges().length()

        while in_id < len(inter.edges) and add_id < len(to_add):
            # projected edges since they represent the stitch sizes
            next_init = covered_init + inter.projecting_edges()[in_id].length() / total_len
            next_added = covered_added + to_add[add_id]
            if close_enough(next_init, next_added, tol):
                # the vertex exists, skip
                in_id += 1
                add_id += 1
                covered_init, covered_added = next_init, next_added
            elif next_init < next_added:
                # add on the next step
                in_id += 1
                covered_init = next_init
            else:
                # add a vertex to the edge at the new location
                # Eval on projected edge
                projected_edge = inter.projecting_edges()[in_id]
                projected_edge_frac = projected_edge.length() / total_len
                new_v_loc = projected_edge_frac - (next_init - next_added)
                frac = new_v_loc / projected_edge_frac
                base_edge = inter.edges[in_id]

                # add with the same fraction to the base edge
                subdiv = EdgeSeqFactory.from_fractions(base_edge.start, base_edge.end, [frac, 1 - frac])

                inter.panel[in_id].edges.substitute(base_edge, subdiv)  # Update the panel
                inter.edges.substitute(base_edge, subdiv)  # interface
                inter.panel.insert(in_id, inter.panel[in_id])  # update panel correspondance

                # TODO what if these edges are used in other interfaces? Do they need to be updated as well?
                # TODO Support the use in other Stitching rules -- multi-way stitches. Some recursion may work

                # next step
                in_id += 1
                add_id += 1
                covered_init += subdiv[0].length() / total_len
                covered_added = next_added

        if add_id != len(to_add):
            raise RuntimeError(f'{self.__class__.__name__}::Error::Projection failed')
                

    def assembly(self):
        """Produce a stitch that connects two interfaces
        """
        if not self.isMatching():
            raise RuntimeError(f'{self.__class__.__name__}::Error::Stitch sides do not match!!')

        stitches = []
        swap = not self.isTraversalMatching()  # traverse edge sequences correctly

        for i, j in zip(range(len(self.int1.edges)), range(len(self.int2.edges) - 1, -1, -1) if swap else range(len(self.int2.edges))):
            stitches.append([
                {
                    'panel': self.int1.panel[i].name,  # corresponds to a name. 
                                            # Only one element of the first level is expected
                    'edge': self.int1.edges[i].geometric_id
                },
                {
                    'panel': self.int2.panel[j].name,
                    'edge': self.int2.edges[j].geometric_id
                }
            ])
        return stitches


class Stitches():
    """Describes a collection of StitchingRule objects
        Needed for more compact specification and evaluation of those rules
    """
    def __init__(self, *rules) -> None:
        """Rules -- any number of tuples of two interfaces (Interface, Interface) """

        self.rules = [StitchingRule(int1, int2) for int1, int2 in rules]

    def append(self, pair):  # TODO two parameters explicitely rather then "pair" object?
        self.rules.append(StitchingRule(*pair))
    
    def assembly(self):
        stitches = []
        for rule in self.rules:
            stitches += rule.assembly()
        return stitches