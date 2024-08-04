import numpy as np

from pygarment.garmentcode.interface import Interface
from pygarment.garmentcode.utils import close_enough


class StitchingRule:
    """High-level stitching instructions connecting two component interfaces
    """
    def __init__(self, int1: Interface, int2: Interface, 
                 verbose: bool = False) -> None:
        """
        Inputs:
            * int1, int2 -- two interfaces to connect in the stitch
        NOTE: When connecting interfaces with multiple edge count on both
            sides,
            1) Note that the edge sequences may change their structure.
                Involved interfaces and corresponding patterns will be updated
                    automatically
                Use of the same interfaces in other stitches (creating 3+way
                    stitch edge) may fail.
            2) The interfaces' edges are matched based on the provided order
                in the interface.
            The order can be controlled at the moment of interface creation
        """
        # TODO Explicitely support 3+way stitches
        self.int1 = int1
        self.int2 = int2
        self.verbose = verbose
        if not self.isMatching():
            self.match_interfaces()

        if verbose and not close_enough(
                len1 := int1.projecting_lengths().sum(),
                len2 := int2.projecting_lengths().sum(),
                tol=0.3):   # NOTE = 3 mm
            print(
                f'{self.__class__.__name__}::WARNING::Projected edges do not match in the stitch: \n'
                f'{len1}: {int1}\n{len2}: {int2}')

    def isMatching(self, tol=0.05):
        # if both the breakdown and relative partitioning is similar

        frac1 = self.int1.projecting_fractions()
        frac2 = self.int2.projecting_fractions()

        return len(self.int1) == len(self.int2) and np.allclose(frac1, frac2, atol=tol)

    def match_interfaces(self):
        """ Subdivide the interface edges on both sides s.t. they are matching 
            and can be safely connected
            (same number of edges on each side and same relative fractions)
        
            Serializable format does not natively support t-stitches, 
            so the longer edges needs to be broken down into matching segments
        """

        # Eval the fractions corresponding to every segment in the interfaces
        # Using projecting edges to match desired gather patterns
        frac1 = self.int1.projecting_fractions()
        frac2 = self.int2.projecting_fractions()
        min_frac = min(min(frac1), min(frac2))  # projection tolerance should not be larger than the smallest fraction

        self._match_to_fractions(self.int1, frac2, tol=min(1e-2, min_frac / 2))

        self._match_to_fractions(self.int2, frac1, tol=min(1e-2, min_frac / 2))


    def _match_to_fractions(self, inter:Interface, to_add, tol=1e-2):
        """Add the vertices at given location to the edge sequence in a given
            interface

        Parameters:
            * inter -- interface to modify
            * to_add -- the faractions of segements to be projected onto the
                edge sequence in the inter
            * tol -- the proximity of vertices when they can be regarded as
                the same vertex.
                    NOTE: tol should be shorter than the smallest expected edge
        """

        # NOTE Edge sequences to subdivide might be disconnected 
        # (even belong to different panels), so we need to subdivide per edge

        # Go over the edges keeping track of their fractions
        add_id, in_id = 0, 0
        covered_init, covered_added = 0, 0
        curr_fractions = inter.projecting_fractions()
        
        while in_id < len(inter.edges) and add_id < len(to_add):
            # projected edges since they represent the stitch sizes
            # NOTE: sometimes overshoots slightly due to error accumulation -> bounding by 1.
            
            next_init = min(covered_init + curr_fractions[in_id], 1.)
            next_added = min(covered_added + to_add[add_id], 1.)
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
                in_frac = curr_fractions[in_id]
                new_v_loc = in_frac - (next_init - next_added)
                split_frac = new_v_loc / in_frac
                base_edge, base_panel = inter.edges[in_id], inter.panel[in_id]

                # Check edge orientation
                flip = inter.needsFlipping(in_id)
                if flip: 
                    split_frac = 1 - split_frac
                    if self.verbose:
                        print(f'{self.__class__.__name__}::INFO::{base_edge} from {base_panel.name} reoriented in interface')

                # Split the base edge accordingly
                subdiv = base_edge.subdivide_len([split_frac, 1 - split_frac])

                inter.panel[in_id].edges.substitute(base_edge, subdiv)  # Update the panel
                                                                        # Always follows the edge order in the panel
                # Swap subdiv order for interface to s.w. the interface sequence remains oriented
                if flip: 
                    subdiv.edges.reverse()
                    
                # Update interface accordingly
                inter.substitute(
                    base_edge, subdiv, [inter.panel[in_id]
                                        for _ in range(len(subdiv))])

                # TODO what if these edges are used in other interfaces? Do they need to be updated as well?
                # next step
                curr_fractions = inter.projecting_fractions()
                covered_init += curr_fractions[in_id]
                covered_added = next_added 
                in_id += 1
                add_id += 1

        if add_id != len(to_add):
            raise RuntimeError(f'{self.__class__.__name__}::ERROR::Projection on {inter.panel_names()} failed')

    def assembly(self):
        """Produce a stitch that connects two interfaces
        """
        if self.verbose and not self.isMatching():
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

            # Swap indication 
            # NOTE: Swap is indicated on the interfaces in order to support component
            # incapsulation. Same stitching rule for different participating components may have different
            # fabric side preferences. 
            # NOTE: "right_wrong" stitch is used when either of the interfaces request it
            # NOTE: Backward-compatible formulation 
            if self.int1.right_wrong[i] or self.int2.right_wrong[j]:  
                stitches[-1].append('right_wrong')

        return stitches


class Stitches:
    """Describes a collection of StitchingRule objects
        Needed for more compact specification and evaluation of those rules
    """
    def __init__(self, *rules) -> None:
        """Rules -- any number of tuples of two interfaces (Interface, Interface) """

        self.rules = [StitchingRule(int1, int2) for int1, int2 in rules]

    def append(self, pair):  # TODOLOW two parameters explicitely rather then "pair" object?
        self.rules.append(StitchingRule(*pair))

    def __getitem__(self, id):
        return self.rules[id]

    def assembly(self):
        stitches = []
        for rule in self.rules:
            stitches += rule.assembly()
        return stitches
