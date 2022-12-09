# Custom
from .edge import LogicalEdge, EdgeSequence

class Interface():
    """Single edge of a panel that can be used for connecting to"""
    def __init__(self, panel, edges):
        """
        Parameters:
            * panel - Panel object
            * edges - LogicalEdge or EdgeSequence -- edges in the panel that are allowed to connect to
        """

        self.panel = panel
        self.edges = edges if isinstance(edges, EdgeSequence) else EdgeSequence(edges)

    def __len__(self):
        return len(self.edges)
    
    def __str__(self) -> str:
        return f'{self.panel.name}: {str(self.edges)}'
    
    def __repr__(self) -> str:
        return self.__str__()


# DRAFT
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
        return len(self.int1) > 1 or len(self.int2) > 1


    def match_edge_count(self):
        """In T-stitches, subdivide single side to match the number of edges 
        on the other side
        
            Serializable format does not natively support t-stitches, 
            so the long edge needs to be broken down into matching segments
            # SIM specific
        """

        print('We are here!!')  # DEBUG

        # Eval the fraction corresponding to every segment in the "from" interface
        fractions = self.int1.edges.fractions()

        print(fractions)  # DEBUG

        # Subdivide edges in the target interface
        base_edge = self.int2.edges[0]
        subdiv = EdgeSequence.from_fractions(base_edge.start, base_edge.end, fractions)
        # Substitute
        self.int2.panel.edges.substitute(base_edge, subdiv)
        self.int2.edges = subdiv

        print(subdiv)  # DEBUG


    def assembly(self):
        """Produce a stitch that connects two interfaces

        NOTE: the interface geometry matching is not checked, and generally not required 
        """
        # TODO Matching direction -- are the edge sequences match traversal orientation ? 

        if not self.isMatching():
            raise RuntimeError(f'{self.__class__.__name__}::Error::Stitch sides do not matched!!')

        stitches = []
        for i in range(len(self.int1.edges)):
            stitches.append([
                {
                    'panel': self.int1.panel.name,  # corresponds to a name. 
                                            # Only one element of the first level is expected
                    'edge': self.int1.edges[i].geometric_id
                },
                {
                    'panel': self.int2.panel.name,
                    'edge': self.int2.edges[i].geometric_id
                }
            ])
        return stitches

# TODO Remove and refactor the code -- this is obsolete
def connect_assembly(int1:Interface, int2:Interface):
    """Produce a stitch that connects two interfaces

        NOTE: the interface geometry matching is not checked, and generally not required 
    """
    # TODO Multiple edges in the interface / geometric ids
    # TODO BEFORE THIS, one should have a projection operator to match the # of egdes on both sides
    # TODO Interface -- check matching (which edge connects to which edge)

    return [
                {
                    'panel': int1.panel.name,  # corresponds to a name. 
                                            # Only one element of the first level is expected
                    'edge': int1.edges.geometric_id
                },
                {
                    'panel': int2.panel.name,
                    'edge': int2.edges.geometric_id
                }
            ]


