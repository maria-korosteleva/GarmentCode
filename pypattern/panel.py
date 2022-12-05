
import numpy as np
from argparse import Namespace
from scipy.spatial.transform import Rotation as R

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
        self.rotation = R.from_euler('XYZ', [0, 0, 0])  # zero rotation
        self.edges = []   # TODO Dummy square?

    def translate_by(self, delta_vector):
        """Translate panel by a vector"""
        self.translation = self.translation + np.array(delta_vector)
    
    def rotate_by(self, delta_rotation):
        """Rotate panel by a given rotation"""
        self.rotation = delta_rotation * self.rotation

    def swap_right_wrong(self):
        """Swap right and wrond sides of the fabric piece. 
            = flip the normal of the 2D panel by re-tracing the edge loop backwards

            NOTE: the 6D placement of panel is not affected
        """
        # Reverse edges
        self.edges.reverse()
        for edge in self.edges:
            edge.flip()
        
        # UPD interfaces to point to the same edges as before
        for interface in self.interfaces:
            interface.edge_id = len(self.edges) - interface.edge_id - 1


    # Build the panel -- get serializable representation
    def assembly(self):
        # TODO Logical VS qualoth assembly?

        panel = Namespace(
            translation=self.translation.tolist(),
            rotation=self.rotation.as_euler('XYZ', degrees=True).tolist(), 
            vertices=[self.edges[0].start], 
            edges=[])

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
