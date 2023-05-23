from copy import copy
from numpy.linalg import norm
import numpy as np

# Custom
from .edge_factory import EdgeSeqFactory
from .interface import Interface
from .generic_utils import close_enough
from . import flags

verbose=flags.VERBOSE

class StitchingRule():
    """High-level stitching instructions connecting two component interfaces
    """
    def __init__(self, int1:Interface, int2:Interface) -> None:
        """
        NOTE: When connecting interfaces with multiple edge count on both sides, 
            1) Note that the edge sequences may change their structure.
                Involved interfaces and corresponding patterns will be updated automatically
                Use of the same interfaces in other stitches (creating 3+way stitch edge) may fail. 
            2) The interfaces' edges are matched based on the provided order in the interface. 
            The order can be controlled at the moment of interface creation
        """
        self.int1 = int1
        self.int2 = int2

        if not self.isMatching():
            self.match_interfaces()

        if verbose and not close_enough(
                len1:=int1.projecting_edges().length(), 
                len2:=int2.projecting_edges().length(), 
                tol=0.3):   # NOTE = 3 mm
            print(
                f'{self.__class__.__name__}::Warning::Projected edges do not match in the stitch: \n'
                f'{len1}: {int1}\n{len2}: {int2}')
    

    def isMatching(self, tol=0.05):
        # if both the breakdown and relative partitioning is similar

        rev_frac1 = self.int1.edges.fractions()
        rev_frac1.reverse()

        return (len(self.int1) == len(self.int2) 
                and (np.allclose(self.int1.edges.fractions(), self.int2.edges.fractions(), atol=tol)
                    or np.allclose(rev_frac1, self.int2.edges.fractions(), atol=tol)
                )
        )


    def match_interfaces(self):
        """ Subdivide the interface edges on both sides s.t. they are matching 
            and can be safely connected
            (same number of edges on each side and same relative fractions)
        
            Serializable format does not natively support t-stitches, 
            so the longer edges needs to be broken down into matching segments
        """

        # Eval the fractions corresponding to every segments in the interfaces
        # Using projecting edges to match desired gather patterns

        # Remember the state of interfaces before projection (for later)
        edges1 = self.int1.edges.copy()
        panels1 = copy(self.int1.panel) 
        frac1 = self.int1.projecting_edges(on_oriented=True).fractions()

        edges2 = self.int2.edges.copy()
        panels2 = copy(self.int2.panel) 
        frac2 = self.int2.projecting_edges(on_oriented=True).fractions()

        self._match_to_fractions(self.int1, frac2, edges2, panels2)
        self._match_to_fractions(self.int2, frac1, edges1, panels1)


    def _match_to_fractions(self, inter:Interface, to_add, edges, panels, tol=1e-3):
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
                in_frac = inter.projecting_edges()[in_id].length() / total_len
                new_v_loc = in_frac - (next_init - next_added)
                split_frac = new_v_loc / in_frac
                base_edge, base_panel = inter.edges[in_id], inter.panel[in_id]

                # Check edge orientation
                flip = inter.needsFlipping(in_id)
                if flip: 
                    split_frac = 1 - split_frac
                    if verbose:
                        print(f'{self.__class__.__name__}::INFO::{base_edge} from {base_panel.name} reoriented in interface')

                # Split the base edge accrordingly
                subdiv = base_edge.subdivide_len([split_frac, 1 - split_frac])

                inter.panel[in_id].edges.substitute(base_edge, subdiv)  # Update the panel
                                                                        # Always follows the edge order in the panel
                # Swap subdiv order for interface to s.w. the interface sequence remains oriented
                if flip: 
                    subdiv.edges.reverse()
                    
                # Update interface accordingly
                inter.edges.substitute(base_edge, subdiv)  
                inter.panel.insert(in_id, inter.panel[in_id]) 
                inter.edges_flipping.insert(in_id, inter.edges_flipping[in_id]) 
                for it in inter.ruffle:  # UPD ruffle indicators
                    if it['sec'][0] > in_id:
                        it['sec'][0] += 1
                    if it['sec'][1] > in_id:
                        it['sec'][1] += 1

                # next step
                # By the size of new edge
                covered_init += inter.projecting_edges()[in_id].length() / total_len 
                covered_added = next_added
                in_id += 1
                add_id += 1

        if add_id != len(to_add):
            raise RuntimeError(f'{self.__class__.__name__}::Error::Projection failed')
                

    def assembly(self):
        """Produce a stitch that connects two interfaces
        """
        if verbose and not self.isMatching():
            print(f'{self.__class__.__name__}::WARNING::Stitch sides do not match on assembly!!')

        stitches = []

        for i, j in zip(range(len(self.int1.edges)), range(len(self.int2.edges))):
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

    def append(self, pair): 
        self.rules.append(StitchingRule(*pair))

    def __getitem__(self, id):
        return self.rules[id]

    def assembly(self):
        stitches = []
        for rule in self.rules:
            stitches += rule.assembly()
        return stitches