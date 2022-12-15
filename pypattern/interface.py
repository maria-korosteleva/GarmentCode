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

        self.panel = panel
        self.edges = edges if isinstance(edges, EdgeSequence) else EdgeSequence(edges)
        self.ruffle = ruffle

    def projecting_edges(self):
        """Return edges shape that should be used when projecting interface onto another panel
            NOTE: reflects current state of the edge object. Call this function again if egdes change (e.g. their direction)
        """
        return self.edges.copy() if abs(self.ruffle - 1) < 1e-3 else self.edges.copy().extend(1 / self.ruffle)

    def __len__(self):
        return len(self.edges)
    
    def __str__(self) -> str:
        return f'{self.panel.name}: {str(self.edges)}'
    
    def __repr__(self) -> str:
        return self.__str__()