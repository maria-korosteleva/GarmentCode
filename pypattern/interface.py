from copy import copy
from numpy.linalg import norm

# Custom
from .edge import EdgeSequence
from .generic_utils import close_enough

# TODO as EdgeSequence wrapper??
class Interface():
    """Description of an interface of a panel or component
        that can be used in stitches as a single unit
    """
    def __init__(self, panel, edges, ruffle=1.):
        """
        Parameters:
            * panel - Panel object
            * edges - Edge or EdgeSequence -- edges in the panel that are allowed to connect to
            * ruffle - ruffle coefficient for a particular edge. Interface object will supply projecting_edges() shape
                s.t. the ruffles with the given rate are created. Default = 1. (no ruffles, smooth connection)
        """

        self.edges = edges if isinstance(edges, EdgeSequence) else EdgeSequence(edges)
        self.panel = [panel for _ in range(len(self.edges))]  # matches every edge 

        # Ruffles are applied to sections
        # Since extending a chain of edges != extending each edge individually
        self.ruffle = [dict(coeff=ruffle, sec=[0, len(self.edges)])]

    def projecting_edges(self, on_oriented=False) -> EdgeSequence:
        """Return edges shape that should be used when projecting interface onto another panel
            NOTE: reflects current state of the edge object. Call this function again if egdes change (e.g. their direction)
        """
        # Per edge set ruffle application
        projected = self.edges.copy() if not on_oriented else self.oriented_edges()
        for r in self.ruffle:
            if not close_enough(r['coeff'], 1, 1e-3):
                projected[r['sec'][0]:r['sec'][1]].extend(1 / r['coeff'])
        
        return projected

    def needsFlipping(self, i):
        """ Check if particular edge should be re-oriented to follow the general direction of the interface
        """
        e = self.edges[i]
        panel = self.panel[i]
        s_3d, end_3d = panel.point_to_3D(e.start), panel.point_to_3D(e.end)

        # Corener cases
        if i == 0:
            next, next_panel = self.edges[(i+1 % len(self.edges))], self.panel[(i+1)  % len(self.edges)]
            next_3d = next_panel.point_to_3D(next.midpoint())

            # check by start vertex
            # NOTE this can misfire in particular 3D orentations
            return norm(s_3d - next_3d) < norm(end_3d - next_3d)
        if i == len(self.edges) - 1:
            prev, prev_panel = self.edges[i-1], self.panel[i-1]
            prev_3d = prev_panel.point_to_3D(prev.midpoint())

            # check by start vertex
            # NOTE this can misfire in particular 3D orentations
            return norm(s_3d - prev_3d) > norm(end_3d - prev_3d)

        # Mid case
        prev, prev_panel = self.edges[i-1], self.panel[i-1]
        next, next_panel = self.edges[(i+1 % len(self.edges))], self.panel[(i+1)  % len(self.edges)]

        # Optimal order in 3D
        prev_3d = prev_panel.point_to_3D(prev.midpoint())
        next_3d = next_panel.point_to_3D(next.midpoint())

        forward_order_dist = norm(s_3d - prev_3d) + norm(end_3d - next_3d)
        flipped_order_dist = norm(s_3d - next_3d) + norm(end_3d - prev_3d)

        return flipped_order_dist < forward_order_dist


    def oriented_edges(self):
        """ Orient the edges withing the interface sequence along the general direction of the interface

            Creates a copy of the interface s.t. not to disturb the original edge objects
        """
        # TODO can we do the same for the edge sub-sequences?
        #  -> midpoint of a sequence is less representative
        #  -> more likely to have weird relative 3D orientations

        # TODO Move this routine to the EdgeSeq class
        # TODO Utilize distance from the end vertex to the next panel as well for stability
        # start -> prev + end -> next or other way around  

        oriented = self.edges.copy()

        for i in range(len(self.edges)):
            if self.needsFlipping(i):
                oriented[i].reverse()
                oriented[i].flipped = True
            else:
                oriented[i].flipped = False
        return oriented


    def __len__(self):
        return len(self.edges)
    
    def __str__(self) -> str:
        # TODO More clear priting? Verbose level options?
        return f'Interface: {[p.name for p in self.panel]}: {str(self.edges)}'
    
    def __repr__(self) -> str:
        return self.__str__()

    def reverse(self):
        """Reverse the order of edges in the interface
            (without updating the edge objects)

            Reversal is useful for reordering interface edges for correct matching in the multi-stitches
        """
        self.edges.edges.reverse()   # TODO Condition on edge sequence reverse 
        self.panel.reverse()

        enum = len(self.edges)
        for r in self.ruffle:
            # Update ids
            r['sec'][0] = enum - r['sec'][0]
            r['sec'][1] = enum - r['sec'][1]
            # Swap
            r['sec'][0], r['sec'][1] = r['sec'][1], r['sec'][0]
        
        return self

    def reorder(self, curr_edge_ids, projected_edge_ids):
        """Change the order of edges from curr_edge_ids to projected_edge_ids in the interface

            Note that the input should prescrive new ordering for all affected edges
            e.g. if moving 0 -> 1, specify the new location for 1 as well
        """
        
        # TODO Edge Sequence Function wrapper?
        for i, j in zip(curr_edge_ids, projected_edge_ids):
            for r in self.ruffle:
                if (i >= r['sec'][0] and i < r['sec'][1] 
                        and (j < r['sec'][0] or j >= r['sec'][1])):
                    raise NotImplementedError(
                        f'{self.__class__.__name__}::Error::reordering between panel-related sub-segments is not supported')
        

        # TODO This is not reliable though!
        new_edges = EdgeSequence()
        new_panel_list = []
        for i in range(len(self.panel)):
            id = i if i not in curr_edge_ids else projected_edge_ids[curr_edge_ids.index(i)]

            # edges
            new_edges.append(self.edges[id])

            # panels
            new_panel_list.append(self.panel[id])
            
        self.edges = new_edges
        self.panel = new_panel_list


    @staticmethod
    def from_multiple(*ints):
        """Create interface from other interfaces: 
            * Allows to use different panels in one interface
            * different ruffle values in one interface
            
            # NOTE the relative order of edges is preserved from the
            original interfaces and the incoming interface sequence
            This order will then be used in the SrtitchingRule when
            determing connectivity between interfaces
        """
        new_int = copy(ints[0])  # shallow copy -- don't create unnecessary objects
        new_int.edges = EdgeSequence()
        new_int.panel = []
        new_int.ruffle = []
        
        for elem in ints:
            shift = len(new_int.edges)
            new_int.ruffle += [copy(r) for r in elem.ruffle]
            for r in new_int.ruffle[-len(elem.ruffle):]:
                r.update(sec=[r['sec'][0] + shift, r['sec'][1] + shift])

            new_int.edges.append(elem.edges)
            new_int.panel += elem.panel 
            
        return new_int 

    @staticmethod
    def _is_order_matching(panel_s, vert_s, panel_1, vert1, panel_2, vert2) -> bool:
        """Check which of the two vertices vert1 (panel_1) or vert2 (panel_2) is closer to the vert_s 
            from panel_s in 3D"""
        s_3d = panel_s.point_to_3D(vert_s)
        v1_3d = panel_1.point_to_3D(vert1)
        v2_3d = panel_2.point_to_3D(vert2)

        return norm(v1_3d - s_3d) < norm(v2_3d - s_3d)
