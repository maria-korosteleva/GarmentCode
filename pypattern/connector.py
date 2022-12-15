from numpy.linalg import norm

# Custom
from .edge_factory import EdgeSeqFactory

class StitchingRule():
    """High-level stitching instructions connecting two component interfaces"""
    def __init__(self, int1, int2) -> None:
        """Supported combinations: 
            * edges-to-edges (same number of edges on both sides, matching order)
            * T-stitch: multiple edges to single edge
        """
        # TODO Multuple edges and multiple panels??
        self.int1 = int1
        self.int2 = int2

        if not self.isMatching() and not self.isT():
            raise ValueError(f'{self.__class__.__name__}::Error::Many-to-many stitches are not supported')
        
        if self.isT(): # swap to always have long single edge at int2 location
            if len(int2) > 1:
                self.int1, self.int2 = int2, int1
            self.match_edge_count()
            

    def isMatching(self):
        return len(self.int1) == len(self.int2)


    def isT(self):
        """Check if we are dealing with T-stitch"""
        return (len(self.int1) > 1 and len(self.int2) == 1) or (len(self.int2) == 1 and len(self.int2) > 1)


    def isTraversalMatching(self):
        """Check if the traversal direction of edge sequences matches or needs to be swapped"""

        if len(self.int1.edges) > 1:
            # Make sure the direction is matching
            # 3D distance between corner vertices
            start_1 = self.int1.panel.point_to_3D(self.int1.edges[0].start)
            start_2 = self.int2.panel.point_to_3D(self.int2.edges[0].start)

            end_1 = self.int1.panel.point_to_3D(self.int1.edges[-1].end)
            end_2 = self.int2.panel.point_to_3D(self.int2.edges[-1].end)
            
            stitch_dist_straight = norm(start_2 - start_1) + norm(end_2 - end_1)
            stitch_dist_reverse = norm(start_2 - end_1) + norm(end_2 - start_1)

            if stitch_dist_reverse < stitch_dist_straight:
                # We need to swap traversal direction
                return False
        return True


    def match_edge_count(self):
        """In T-stitches, subdivide single side to match the number of edges 
        on the other side
        
            Serializable format does not natively support t-stitches, 
            so the long edge needs to be broken down into matching segments
            # SIM specific
        """

        # Eval the fraction corresponding to every segment in the "from" interface
        fractions = self.int1.edges.fractions()
        if not self.isTraversalMatching():      # Make sure connectivity order will be correct even if edge directions are not aligned
            fractions.reverse()

        # Subdivide edges in the target interface
        base_edge = self.int2.edges[0]
        subdiv = EdgeSeqFactory.from_fractions(base_edge.start, base_edge.end, fractions)
        # Substitute
        self.int2.panel.edges.substitute(base_edge, subdiv)
        self.int2.edges = subdiv


    def assembly(self):
        """Produce a stitch that connects two interfaces

        NOTE: the interface geometry matching is not checked, and generally not required 
        """
        # TODO Matching direction -- are the edge sequences match traversal orientation ? 

        if not self.isMatching():
            raise RuntimeError(f'{self.__class__.__name__}::Error::Stitch sides do not matched!!')

        stitches = []
        swap = not self.isTraversalMatching()  # traverse edge sequences correctly
        for i, j in zip(range(len(self.int1.edges)), range(len(self.int2.edges) - 1, -1, -1) if swap else range(len(self.int2.edges))):
            stitches.append([
                {
                    'panel': self.int1.panel.name,  # corresponds to a name. 
                                            # Only one element of the first level is expected
                    'edge': self.int1.edges[i].geometric_id
                },
                {
                    'panel': self.int2.panel.name,
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

    def append(self, pair):
        self.rules.append(StitchingRule(*pair))
    
    def assembly(self):
        stitches = []
        for rule in self.rules:
            stitches += rule.assembly()
        return stitches