import numpy as np
from copy import copy
from argparse import Namespace
from scipy.spatial.transform import Rotation as R

# Custom
from external.pattern.core import BasicPattern
from .base import BaseComponent
from .edge import Edge, EdgeSequence
from .generic_utils import close_enough, vector_align_3D


class Panel(BaseComponent):
    """ A Base class for defining a Garment component corresponding to a single flat fiece of fabric
    
    Defined as a collection of edges on a 2D grid with specified 3D placement (world coordinates)
    
    NOTE: All operations methods return 'self' object to allow sequential applications

    """
    def __init__(self, name) -> None:
        super().__init__(name)

        self.translation = np.zeros(3)
        self.rotation = R.from_euler('XYZ', [0, 0, 0])  # zero rotation
        # NOTE: initiating with empty sequence allows .append() to it safely
        self.edges =  EdgeSequence() 

    # Info
    # DRAFT 
    def is_right_inside_edge(self, edge:Edge):
        """ Check if the inside of the panel is on the right side
            of an edge
        """
        # FIXME This one is not working reliably =(
        norm = self.norm()

        test_edge = edge.linearize()
        if isinstance(test_edge, EdgeSequence): 
            # NOTE: side is the same for all edges in linearized sequence
            # so it's enough to chech just one
            test_edge = test_edge[0]

        test_edge_3d = [self.point_to_3D(test_edge.start), self.point_to_3D(test_edge.end)]
        test_vec_3d = test_edge_3d[1] - test_edge_3d[0]

        center_of_mass = self.point_to_3D(self._center_2D())

        # We can determine the side based on relationship between the norm and 
        # the edge
        # Knowing that the norm is defined by counterclockwise direction of edges
        cross = np.cross(test_vec_3d, center_of_mass - test_edge_3d[0])

        return np.dot(cross, norm) < 0

    def pivot_3D(self):
        """Pivot point of a panel in 3D"""
        return self.point_to_3D([0, 0])

    # ANCHOR - Operations -- update object in-place 
    def set_pivot(self, point_2d, replicate_placement=False):
        """Specify 2D point w.r.t. panel local space
            to be used as pivot for translation and rotation

        Parameters:
            * point_2d -- desired point 2D point w.r.t current pivot (origin) of panel local space
            * replicate_placement -- will replicate the location of the panel as it was before pivot change
                default - False (no adjustment, the panel may "jump" in 3D)
        """
        point_2d = copy(point_2d)  # Remove unwanted object reference 
                                   # In case an actual vertex was used as a target point

        if replicate_placement:
            self.translation = self.point_to_3D(point_2d)

        # UPD vertex locations relative to new pivot
        for v in self.edges.verts():
            v[0] -= point_2d[0]
            v[1] -= point_2d[1]

    def top_center_pivot(self):
        """One of the most useful pivots 
            is the one in the middle of the top edge of the panel 
        """
        vertices = np.asarray(self.edges.verts())

        # out of 2D bounding box sides' midpoints choose the one that is highest in 3D
        top_right = vertices.max(axis=0)
        low_left = vertices.min(axis=0)
        mid_x = (top_right[0] + low_left[0]) / 2
        mid_y = (top_right[1] + low_left[1]) / 2
        mid_points_2D = [
            [mid_x, top_right[1]], 
            [mid_x, low_left[1]],
            [top_right[0], mid_y],
            [low_left[0], mid_y]
        ]
        mid_points_3D = np.vstack(tuple(
            [self.point_to_3D(coords) for coords in mid_points_2D]
        ))
        top_mid_point = mid_points_3D[:, 1].argmax()

        self.set_pivot(mid_points_2D[top_mid_point])

        return self

    def translate_by(self, delta_vector):
        """Translate panel by a vector"""
        self.translation = self.translation + np.array(delta_vector)
        # TODO Autonorm only on the assembly?
        self.autonorm()

        return self
    
    def translate_to(self, new_translation):
        """Set panel translation to be exactly that vector"""
        self.translation = np.asarray(new_translation)
        self.autonorm()

        return self
    
    def rotate_by(self, delta_rotation: R):
        """Rotate panel by a given rotation
            * delta_rotation: scipy rotation object
        """
        self.rotation = delta_rotation * self.rotation
        self.autonorm()

        return self

    def rotate_to(self, new_rot: R):
        """Set panel rotation to be exactly the given rotation
            * new_rot: scipy rotation object
        """   
        if not isinstance(new_rot, R):
            raise ValueError(f'{self.__class__.__name__}::Error::Only accepting rotations in scipy format')
        self.rotation = new_rot
        self.autonorm()

        return self

    def rotate_align(self, vector):
        """Set panel rotation s.t. it's norm is aligned with a given 3D vector"""

        vector = np.asarray(vector)
        vector = vector / np.linalg.norm(vector)
        n = self.norm()
        self.rotate_by(vector_align_3D(n, vector))

        return self

    def center_x(self):
        """Adjust translation over x s.t. the center of the panel is aligned with the Y axis (center of the body)"""

        center_3d = self.point_to_3D(self._center_2D())
        self.translation[0] += -center_3d[0]

        return self

    def autonorm(self):
        """Update right/wrong side orientation, s.t. the normal of the surface looks outside of the world origin, 
            taking into account the shape and the global position.
        
            This should provide correct panel orientation in most cases.

            NOTE: for best results, call autonorm after translation specification
        """
        norm_dr = self.norm()
        
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
        if close_enough(axis[0], tol=1e-4):  # reflection around Y

            # Vertices
            self.edges.reflect([0, 0], [0, 1])
            
            # Position
            self.translation[0] *= -1

            # Rotations
            curr_euler = self.rotation.as_euler('XYZ')
            curr_euler[1] *= -1  
            curr_euler[2] *= -1  
            self.rotate_to(R.from_euler('XYZ', curr_euler))  

            # Fix right/wrong side
            self.autonorm()
        else:
            # TODO Any other axis
            raise NotImplementedError(f'{self.name}::Error::Mirrowing over arbitrary axis is not implemented')

        return self
        
    # ANCHOR - Build the panel -- get serializable representation
    def assembly(self):
        """Convert panel into serialazable representation
        
         # SIM Note that Qualoth simulator does not support internal loops in panels,
            hence panel EdgeSequence is assumed to be a single loop of edges
        """
        # always start from zero for consistency between panels
        self.set_pivot(self.edges[0].start, replicate_placement=True)

        # Basics
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
                vert_shift = len(panel.vertices)
                panel.vertices += vertices

            # upd vertex references in edges according to new vertex ids in 
            # the panel vertex loop
            edge['endpoints'] = [id + vert_shift for id in edge['endpoints']]
                
            edge_shift = len(panel.edges)  # before adding new ones
            self.edges[i].geometric_id = edge_shift   # remember the mapping of logical edge to geometric id in panel loop
            panel.edges.append(edge)

        # Check closing of the loop and upd vertex reference for the last edge
        if panel.vertices[-1] == panel.vertices[0]:
            panel.vertices.pop()
            panel.edges[-1]['endpoints'][-1] = 0

        spattern = BasicPattern()
        spattern.name = self.name
        spattern.pattern['panels'] = {self.name: vars(panel)}

        # Assembly stitching info (panel might have inner stitches)
        spattern.pattern['stitches'] = self.stitching_rules.assembly()
            
        return spattern

    # ANCHOR utils
    def _center_2D(self):
        """Approximate Location of the panel center. 
            
            NOTE: uses crude linear approximation for curved edges
        """
        # NOTE: assuming that edges are organized in a loop and share vertices
        lin_edges = EdgeSequence([e.linearize() for e in self.edges])
        verts = lin_edges.verts()

        return np.mean(verts, axis=0)

    def point_to_3D(self, point_2d):
        """Calculate 3D location of a point given in the local 2D plane """
        point_2d = np.asarray(point_2d)
        if len(point_2d) == 2:
            point_2d = np.append(point_2d, 0)

        point_3d = self.rotation.apply(point_2d)
        point_3d += self.translation

        return point_3d

    def norm(self):
        """Normal direction for the current panel"""

        # Take linear version of the edges
        # To correctly process edges with extreme curvatures
        lin_edges = EdgeSequence([e.linearize() for e in self.edges])

        # center of mass
        verts = lin_edges.verts()

        center = np.mean(verts, axis=0)
        center_3d = self.point_to_3D(center)

        # To make norm evaluation work for non-convex panels
        # Evalute norm candidates for all edges and then weight them. 
        # The dominant norm direction should be the correct one 
        norms = []
        for e in lin_edges:
            vert_0 = self.point_to_3D(e.start)
            vert_1 = self.point_to_3D(e.end)

            # TODO Use subpoints for curvy edges (they can be very long)
            # Maybe just the midpoint would give a general idea. 
            # Otherwise, use "peak" points of a curvy edge

            # Pylance + NP error for unreachanble code -- see https://github.com/numpy/numpy/issues/22146
            # Works ok for numpy 1.23.4+
            norm = np.cross(vert_1 - vert_0, center_3d - vert_0)
            norm /= np.linalg.norm(norm)
            norms.append(norm)

        # Current norm direction
        avg_norm = sum(norms) / len(norms)
        return avg_norm / np.linalg.norm(avg_norm)

    def bbox3D(self):
        """Evaluate 3D bounding box of the current panel"""

        # Using curve linearization for more accurate approximation of bbox
        lin_edges = EdgeSequence([e.linearize() for e in self.edges])
        verts_2d = lin_edges.verts()
        verts_3d = np.asarray([self.point_to_3D(v) for v in verts_2d])

        return verts_3d.min(axis=0), verts_3d.max(axis=0)
