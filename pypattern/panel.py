
import numpy as np
from argparse import Namespace

# Custom
from .component import Component 

class Panel(Component):
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

    # DRAFT
    def connect(self, interf_id, connected_panel, target_interf_id):
        pass

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

            # TODO account for connecting edges being different from 
            # Geometric pattern description

            # upd vertex references in edges according to new vertex ids in 
            # the panel vertex loop
            vert_shift = len(panel.vertices) - 1
            edge_shift = len(panel.edges) - 1
            for edge in edges:
                edge['endpoints'] = [id + vert_shift for id in edge['endpoints']]

            self.edges[i].geometric_ids = [id + edge_shift for id in len(edges)]   # remember the mapping of logical edge to geometric edge
            panel.edges += edges

            # add new vertices
            if panel.vertices[-1] == vertices[0]:  # TODO is this correct way to compare object references?
                panel.vertices += vertices[1:] 
            else: 
                # TODO Proper handling of multiple loops in the same pattern
                panel.vertices += vertices

        # Check closing of the loop and upd vertex reference for the last edge
        # TODO multiple loops in panel
        if panel.vertices[-1] == panel.vertices[0]:
            panel.vertices.pop()
            panel.edges[-1]['endpoints'][-1] = 0


        return {'panels': {self.name: vars(panel)}}