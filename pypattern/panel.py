
import numpy as np

# Custom
from .component import Component
from .edge import Edge

class Panel(Component):
    """Lowest level of garment component correspnding to a single flat fiece of fabric
    
    Defined as a collection of edges on a 2D grid with specified 3D placement (world coordinates)
    
    """

    def __init__(self, ) -> None:
        super().__init__()

        self.translation = np.zeros(3)
        self.rotation = np.zeros(3)
        self.edges = []
        self.vertices = []

    def assembly(self):
        return super().assembly()