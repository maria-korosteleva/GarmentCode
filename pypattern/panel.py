
import numpy as np
from argparse import Namespace
from scipy.spatial.transform import Rotation as R

# Custom
from pattern.core import BasicPattern
from pattern.wrappers import VisPattern
from .base import BaseComponent
from .edge import EdgeSequence

class Panel(BaseComponent):
    """ A Base class for defining a Garment component corresponding to a single flat fiece of fabric
    
    Defined as a collection of edges on a 2D grid with specified 3D placement (world coordinates)
    
    NOTE: All operations methods return 'self' object to allow sequential applications

    """
    # TODO __get_item__ implementation? Return edges??

    def __init__(self, name) -> None:
        super().__init__(name)

        self.translation = np.zeros(3)  # TODO translation location? relative to what?
        self.rotation = R.from_euler('XYZ', [0, 0, 0])  # zero rotation
        self.edges =  EdgeSequence()  # TODO Dummy square?

    # ANCHOR - Operations -- update object in-place 
    def translate_by(self, delta_vector):
        """Translate panel by a vector"""
        self.translation = self.translation + np.array(delta_vector)
        self.autonorm()

        return self
    
    def rotate_by(self, delta_rotation):
        """Rotate panel by a given rotation"""
        self.rotation = delta_rotation * self.rotation
        self.autonorm()

        return self

    def center_x(self):
        """Adjust translation over x s.t. the center of the panel is aligned with the Y axis (center of the body)"""

        center_3d = self._point_to_3d(self._center_2d())
        self.translation[0] += -center_3d[0]

        return self

    def autonorm(self):
        """Update right/wrong side orientation, s.t. the normal of the surface looks outside of the world origin, 
            taking into account the shape and the global position.
        
            This should provide correct panel orientation in most cases.

            NOTE: for best results, call autonorm after translation specification
        """

        # Current norm direction 
        first_edge_dr = np.append((np.array(self.edges[0].end) - np.array(self.edges[0].start)), 0)  # eval and make 3D
        last_edge_dr = np.append((np.array(self.edges[-1].start) - np.array(self.edges[-1].end)), 0)  # eval and make 3D

        # Account for panel rotation
        first_edge_dr = self.rotation.apply(first_edge_dr)
        last_edge_dr = self.rotation.apply(last_edge_dr)

        # Pylance + NP error for unreachanble code -- see https://github.com/numpy/numpy/issues/22146
        # Works ok for numpy 1.23.4+
        norm_dr = np.cross(first_edge_dr, last_edge_dr)  # TODO Check the order
        
        # NOTE: Nothing happens if self.translation is zero
        if np.dot(norm_dr, self.translation) < 0: 
            # Swap if wrong
            self.edges.reverse()
        
        return self

    def mirror(self, axis=[0, 1]):
        """Swap this panel with it's mirror image
        
            Axis specifies 2D axis to swap around: Y axis by default
        """

        # Case Around Y
        if abs(axis[0]) < 1e-4:  # reflection around Y

            # Vertices
            for i in range(len(self.edges) - 1):
                # Swap the x of end vertex only 
                # TODO multiple edge loops??
                self.edges[i].end[0] *= -1
            
            # Position
            self.translation[0] *= -1

            # Fix right/wrong side
            self.autonorm()

            # NOTE: Origin vertex is not updated -- and may now be on the right of the edge rather then on the left
            # TODO Update origin vertex as well
        else:
            # TODO Any other axis
            raise NotImplementedError(f'{self.name}::Error::Mirrowing over arbitrary axis is not implemented')

        return self
        
    # ANCHOR - Build the panel -- get serializable representation
    def assembly(self):
        # TODO Logical VS qualoth assembly?

        panel = Namespace(
            translation=self.translation.tolist(),
            rotation=self.rotation.as_euler('XYZ', degrees=True).tolist(), 
            vertices=[self.edges[0].start], 
            edges=[])

        for i in range(len(self.edges)):
            vertices, edge = self.edges[i].assembly()

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
            edge['endpoints'] = [id + vert_shift for id in edge['endpoints']]
                
            edge_shift = len(panel.edges)  # before adding new ones
            self.edges[i].geometric_id = edge_shift   # remember the mapping of logical edge to geometric id in panel loop
            panel.edges.append(edge)

        # Check closing of the loop and upd vertex reference for the last edge
        # TODO multiple loops in panel
        if panel.vertices[-1] == panel.vertices[0]:
            panel.vertices.pop()
            panel.edges[-1]['endpoints'][-1] = 0

        spattern = BasicPattern()
        spattern.name = self.name
        spattern.pattern['panels'] = {self.name: vars(panel)}

        # Assembly stitching info (panel might have inner stitches)
        for rule in self.stitching_rules:
            spattern.pattern['stitches'] += rule.assembly()
            
        return spattern

    # ANCHOR utils
    def _center_2d(self):
        """Location of the panel center. NOTE: does not account for the curvatures
        """
        # NOTE: assuming that edges are organized in a loop and share vertices
        # TODO general case for multiple loops?
        # TODO Account for curvatures?
        center_2d = np.array([
            sum([edge.start[0] + edge.end[0] for edge in self.edges]), 
            sum([edge.start[1] + edge.end[1] for edge in self.edges])
            ])

        return center_2d / (2 * len(self.edges))

    def _point_to_3d(self, point_2d):
        """Calculate 3D location of a point given in the local 2D plane """
        point_2d = np.asarray(point_2d)
        if len(point_2d) == 2:
            point_2d = np.append(point_2d, 0)

        point_3d = self.rotation.apply(point_2d)
        point_3d += self.translation

        return point_3d

