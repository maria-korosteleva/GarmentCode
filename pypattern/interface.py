from copy import copy
from numpy.linalg import norm

# Custom
from .edge import EdgeSequence
from .generic_utils import close_enough

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
        self.ruffle = [dict(coeff=ruffle, sec=(0, len(self.edges)))]

    def projecting_edges(self) -> EdgeSequence:
        """Return edges shape that should be used when projecting interface onto another panel
            NOTE: reflects current state of the edge object. Call this function again if egdes change (e.g. their direction)
        """
        # Per edge set ruffle application
        projected = self.edges.copy()
        for r in self.ruffle:
            if not close_enough(r['coeff'], 1, 1e-3):
                projected[r['sec'][0]:r['sec'][1]].extend(1 / r['coeff'])
        
        return projected

    def __len__(self):
        return len(self.edges)
    
    def __str__(self) -> str:
        # TODO More clear priting? Verbose level options?
        return f'Interface: {[p.name for p in self.panel]}: {str(self.edges)}'
    
    def __repr__(self) -> str:
        return self.__str__()

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
                r.update(sec=(r['sec'][0] + shift, r['sec'][1] + shift))

            new_int.edges.append(elem.edges)
            new_int.panel += elem.panel 
            
        return new_int 

    @staticmethod
    def _is_order_matching(panel_s, vert_s, panel_1, vert1, panel_2, vert2) -> bool:
        """Check which of the vertices from panel_t is closer to the vert_s 
            from panel_s in 3D"""
        s_3d = panel_s.point_to_3D(vert_s)
        v1_3d = panel_1.point_to_3D(vert1)
        v2_3d = panel_2.point_to_3D(vert2)

        return norm(v1_3d - s_3d) < norm(v2_3d - s_3d)
