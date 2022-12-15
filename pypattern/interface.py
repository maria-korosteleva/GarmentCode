# Custom
from .edge import EdgeSequence

class Interface():
    """Description of an interface of a panel or component
        that can be used in stitches as a single unit
    """
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