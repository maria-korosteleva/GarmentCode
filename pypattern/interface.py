from copy import copy
from numpy.linalg import norm

# Custom
from .edge import EdgeSequence

class Interface():
    """Description of an interface of a panel or component
        that can be used in stitches as a single unit
    """
    def __init__(self, panel, edges, ruffle=1.):
        """
        Parameters:
            * panel - Panel object
            * edges - LogicalEdge or EdgeSequence -- edges in the panel that are allowed to connect to
            * ruffle - ruffle coefficient for a particular edge. Interface object will supply projecting_edges() shape
                s.t. the ruffles with the given rate are created. Default = 1. (no ruffles, smooth connection)
        """

        self.edges = edges if isinstance(edges, EdgeSequence) else EdgeSequence(edges)
        self.panel = [panel for _ in range(len(self.edges))]  # matches every edge 
        self.ruffle = ruffle

    def projecting_edges(self):
        """Return edges shape that should be used when projecting interface onto another panel
            NOTE: reflects current state of the edge object. Call this function again if egdes change (e.g. their direction)
        """
        return self.edges.copy() if abs(self.ruffle - 1) < 1e-3 else self.edges.copy().extend(1 / self.ruffle)    

    def __len__(self):
        return len(self.edges)
    
    def __str__(self) -> str:
        return f'{[p.name for p in self.panel]}: {str(self.edges)}'
    
    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def from_multiple(*ints):
        """Create interface from other interfaces: 
            * Allows to use different panels in one interface
            * different ruffle values in one interface
        """
        new_int = copy(ints[0])  # shallow copy -- don't create unnecessary objects
        new_int.edges = EdgeSequence()
        new_int.panel = []
        
        for elem in ints:
            # Adding edges while aligning their order right away!
            # (following the same clockwise/counterclockwise orientation regardless of 
            # in-panel orientation)
            if len(new_int.panel) > 0 and not Interface._is_order_matching(
                new_int.panel[-1], new_int.edges[-1].end,
                elem.panel[0], elem.edges[0].start,
                elem.panel[-1], elem.edges[-1].start   # start or end -- anything works for this check
            ):
                # swap the order of new edges
                to_add = EdgeSequence(elem.edges)  # Edge sequence object with the same edge objects
                to_add.edges.reverse()  # reverse the order of edge objects withough flippling them
                
                to_add_panels = copy(elem.panel)
                to_add_panels.reverse()  # shallow copy
            else:
                to_add = elem.edges
                to_add_panels = elem.panel 

            new_int.edges.append(to_add)
            new_int.panel += to_add_panels
            
        return new_int   # TODO ruffles as well!

    @staticmethod
    def _is_order_matching(panel_s, vert_s, panel_1, vert1, panel_2, vert2):
        """Check which of the vertices from panel_t is closer to the vert_s 
            from panel_s in 3D"""
        s_3d = panel_s.point_to_3D(vert_s)
        v1_3d = panel_1.point_to_3D(vert1)
        v2_3d = panel_2.point_to_3D(vert2)

        return norm(v1_3d - s_3d) < norm(v2_3d - s_3d)
