
import numpy as np
from argparse import Namespace

# Custom
from pattern.core import BasicPattern
from .base import BaseComponent

class Panel(BaseComponent):
    """ Garment component correspnding to a single flat fiece of fabric
    
    Defined as a collection of edges on a 2D grid with specified 3D placement (world coordinates)
    
    """

    def __init__(self, name) -> None:
        super().__init__(name)

        self.translation = np.zeros(3)  # TODO translation location? relative to what?
        self.rotation = np.zeros(3)
        self.edges = []   # TODO Dummy square?

    def translate(self, vector):
        # TODO Or _by_ a vector?
        self.translation = np.array(vector)
    
    def rotate(self, rotation):
        # TODO Or _by_ a rotation?
        self.rotation = np.array(rotation)

    def assembly(self):
        # TODO Logical VS qualoth assembly?

        panel = Namespace(
            translation=self.translation.tolist(),
            rotation=self.rotation.tolist(),  # TODO Correct format?
            vertices=[self.edges[0].start], 
            edges=[],
            connecting_ids=[None] * len(self.interfaces))

        for i in range(len(self.edges)):
            vertices, edges = self.edges[i].assembly()

            # add new vertices
            if panel.vertices[-1] == vertices[0]:   # We care if both point to the same vertex location, not necessarily the same vertex object
                vert_shift = len(panel.vertices) - 1  # first edge vertex = last vertex already in the loop
                panel.vertices += vertices[1:] 
            else: 
                # TODO Proper handling of multiple loops in the same pattern
                vert_shift = len(panel.vertices)
                panel.vertices += vertices

            # upd vertex references in edges according to new vertex ids in 
            # the panel vertex loop
            for edge in edges:       
                edge['endpoints'] = [id + vert_shift for id in edge['endpoints']]
                
            # TODO account for connecting edges being different from 
            # Geometric pattern description
            edge_shift = len(panel.edges)  # before adding new ones
            self.edges[i].geometric_ids = [id + edge_shift for id in range(len(edges))]   # remember the mapping of logical edge to geometric edge
            panel.edges += edges

        # Check closing of the loop and upd vertex reference for the last edge
        # TODO multiple loops in panel
        if panel.vertices[-1] == panel.vertices[0]:
            panel.vertices.pop()
            panel.edges[-1]['endpoints'][-1] = 0

        spattern = BasicPattern()
        spattern.name = self.name
        spattern.pattern['panels'] = {self.name: vars(panel)}

        return spattern
