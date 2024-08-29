"""
    Module contains classes needed to generate a box
    mesh from patterns and simulate it using warp
"""

#Basic
import igl
import numpy as np
import math
import svgpathtools as svgpath
import matplotlib.pyplot as plt
import shutil
import pickle
from pathlib import Path   
import yaml
from typing import List, Dict, Tuple

#Personal Modules
import pygarment.pattern.core as core
import pygarment.pattern.wrappers as wrappers
from pygarment.pattern import rotation as rotation_tools
import pygarment.pattern.utils as pat_utils
import pygarment.meshgen.triangulation_utils as tri_utils
from pygarment.meshgen.sim_config import PathCofig
from pygarment.meshgen.render.texture_utils import texture_mesh_islands, save_obj

# TODOLOW Some stitching errors are not getting detected

# SECTION -- Errors
class PatternLoadingError(BaseException):
    """To be raised when a pattern cannot be loaded correctly to 3D"""
    pass

class MultiStitchingError(BaseException):
    """To be raised when a panel edge is stitched together with more than one other edge"""
    pass

class StitchingError(BaseException):
    """To be raised when a one cannot find successfull stitching sequence"""
    pass

class DegenerateTrianglesError(BaseException):
    """To be raised when panel meshing produces degenrate triangles"""
    pass

class NormError(BaseException):
    """To be raised when a panel norm is NAN"""
    pass
# !SECTION
# SECTION Mesh objects
class Panel:
    """
    Represents a panel of the pattern:
        Input:
            * panel: panel information
            * panelName: panel name
    """
    def __init__(self, panel, panelName, mesh_resolution):

        self.panel_name = panelName
        self.translation = np.asarray(panel['translation'])
        self.rotation = np.asarray(panel['rotation'])
        self.corner_vertices = np.asarray(panel['vertices'])
        self.panel_vertices = []
        self.panel_faces = []
        self.edges: List[Edge] = []
        self.n_stitches = 0 #needed later to decide whether vertex is stitch vertex or not
        self.glob_offset = -1

        for edge in np.asarray(panel['edges']):
            edge_obj = Edge(edge, self.corner_vertices, mesh_resolution)
            self.edges.append(edge_obj)

        self.norm = []


    def _verts(self, lin_edges):
        """
        This function takes a sequence of linear edges and processes them to extract unique vertices.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * lin_edges (list): Sequence of edges defined by their start and end vertices
        Output:
            * verts (list): List of unique vertices extracted from lin_edges, arranged in the order they were encountered
        """
        verts = [lin_edges[0][0]]
        for e in lin_edges:
            if not np.array_equal(e[0], verts[-1]):  # avoid adding the vertices of chained edges twice
                verts.append(e[0])
            verts.append(e[1])
        if np.array_equal(verts[0], verts[-1]):  # don't double count the loop origin
            verts.pop(-1)
        return verts


    def _bbox(self, verts_2d):
        """
        This function evaluates the 2D bounding box of the current panel and returns the panel vertices which are
        located on the bounding box (b_points) as well as the mean point of b_points in 3D.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * verts_2d (list): List of 2D panel edge vertices ordered in a loop
        Output:
            * b_points_mean_3d (ndarray): 3D vertex representing the rotated and translated mean point of b_points,
            i.e., the vertices of verts_2d located on the bounding box
            * b_points_3d (ndarray): Ndarray of 3D vertices representing the rotated and translated b_points, i.e.,
              the vertices of verts_2d located on the bounding box
        """
        verts_2d_arr = np.array(verts_2d)
        mi = verts_2d_arr.min(axis=0)
        ma = verts_2d_arr.max(axis=0)
        xs = [mi[0],ma[0]]
        ys = [mi[1],ma[1]]
        #return points on bounding box
        b_points = []
        for v in verts_2d_arr:
            if v[0] in xs or v[1] in ys:
                b_points.append(v)
        if len(b_points) == 2:
            if not any(np.array_equal(arr, mi) for arr in b_points):
                b_points = [b_points[0], mi, b_points[1]]
            else:
                p = [mi[0],ma[1]]
                b_points = [b_points[0],p,b_points[1]]
        elif len(b_points) < 2:
            raise PatternLoadingError("Less than two vertices defining bounding box")

        b_points_3d = self.rot_trans_panel(b_points)
        b_points_mean_2d = np.mean((b_points),axis=0)
        b_points_mean_3d = self.rot_trans_vertex(b_points_mean_2d)

        plot_pts = b_points + [b_points_mean_2d]
        # self.plot(plot_pts, f"{self.panel_name} BBOX")
        return b_points_mean_3d, b_points_3d


    def plot(self, pts, title):
        """
        This function creates a scatter plot of points (used for debugging).
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * pts (list): Points to be plotted
            * title (str): Title of the scatter plot
        """
        pts = np.array(pts)
        x_values = pts.T[0]
        y_values = pts.T[1]
        plt.scatter(x_values, y_values, c='blue', marker='o', label='Data Points')

        # Annotate the data points with text
        for i in range(len(x_values)):
            plt.annotate(f'{i}', (x_values[i], y_values[i]), textcoords="offset points", xytext=(0, 5), ha='center')

        # Customize the plot (optional)
        plt.title(title)
        plt.xlabel('X-axis')
        plt.ylabel('Y-axis')
        plt.legend()
        # plt.axis('square')

        # Show the plot
        plt.show()


    def set_panel_norm(self):
        """
        This function computes the normal direction of the current panel.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
        """

        # Take linear version of the edges
        # To correctly process edges with extreme curvatures
        lin_edges = []
        for e in self.edges:
            lin_edges += list(e.linearize(self))

        verts = self._verts(lin_edges)
        # self.plot(verts, f"{self.panel_name} VERTS")

        center_3d, verts_3d = self._bbox(verts)

        norms = []
        num_verts_3d = len(verts_3d)
        for i in range(num_verts_3d):
            vert_0 = verts_3d[i]
            vert_1 = verts_3d[(i+1) % num_verts_3d]
            # Pylance + NP error for unreachanble code -- see https://github.com/numpy/numpy/issues/22146
            # Works ok for numpy 1.23.4+
            norm = np.cross(vert_0-center_3d, vert_1-center_3d)
            norm /= np.linalg.norm(norm)
            norms.append(norm)

        # Current norm direction
        avg_norm = sum(norms) / len(norms)
        #final_norm = list(avg_norm / np.linalg.norm(avg_norm)) #before
        if np.linalg.norm(avg_norm) == 0 or np.any(np.isnan(avg_norm)):
            raise NormError(f"{self.__class__.__name__}::ERROR::invalid panel norm for {self.panel_name}; "
                             f"norms: {norms}; avg_norm: {avg_norm}")
        else:
            final_norm = list(avg_norm / np.linalg.norm(avg_norm))

        #solve float errors
        for i, ni in enumerate(final_norm):
            if np.isclose([ni], [0.0]):
                final_norm[i] = 0.0

        self.norm = final_norm


    def rot_trans_vertex(self, vertex):
        """
        This function transforms a 2D vertex into a 3D vertex by rotating it with
        respect to the XYZ Euler angles and applying the specified translation.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * vertex (numpy array): Coorindates of the 2D vertex to be transformed
        Output:
            * r_t_vertex (numpy array): Coordinates of the rotated and translated 3D vertex
        """

        rot_matrix = rotation_tools.euler_xyz_to_R(self.rotation)
        r_t_vertex = BoxMesh._point_in_3D(vertex, rot_matrix, self.translation)
        return r_t_vertex


    def rot_trans_panel(self, vertices):
        """
        This function transforms multiple 2D vertices into 3D vertices by rotating them with
        respect to the XYZ Euler angles and applying the specified translation.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * vertices (numpy ndarray): Coorindates of the 2D vertices to be transformed
        Output:
            * r_t_vertices (numpy ndarray): Coordinates of the rotated and translated 3D vertices
        """
        if len(vertices) == 0:
            return []
        rot_matrix = rotation_tools.euler_xyz_to_R(self.rotation)
        r_t_vertices = np.vstack(tuple([BoxMesh._point_in_3D(v, rot_matrix, self.translation) for v in np.array(vertices)]))
        return r_t_vertices


    def _get_exist_idx(self, find_list):
        """
        This function returns the index of find_list (start or end vertex) in panel.panel_vertices.
        If find_list is not in panel.panel_vertices, find_list is first added to panel.panel_vertices.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * find_list (ndarray): Either start or end vertex of an edge
        Output:
            * (int): Index of find_list (start or end vertex) in panel.panel_vertices
        """
        pvertices = np.array(self.panel_vertices)

        len_pvertices = len(pvertices)
        if len_pvertices == 0:
            self.panel_vertices.append(find_list)
            return 0

        else:
            index = np.where(np.all(pvertices == find_list, axis=1))
            n_found_indices = len(index[0])

            if n_found_indices == 1:  # get index
                return index[0][0]
            elif n_found_indices == 0:
                self.panel_vertices.append(find_list)
                return len(self.panel_vertices) - 1
            else: #n_found_indices > 1
                raise PatternLoadingError(
                    f'{self.__class__.__name__}::{self.name}::Corner stitch vertex has been added more than once to panel vertices!')


    def store_edge_verts(self, edge, edge_in_vertices):
        """
        This function stores the panel.panel_vertices indices of the "start" vertex,
        "edge_in_vertices" vertices, and "end" vertex of edge into edge.vertex_range
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * edge (Edge object): Instance of Edge class whose vertex indices are stored
            * edge_in_vertices (list): Equally spread vertices along edge (without start and end vertex)
        """
        start, end = edge.endpoints
        start_index = self._get_exist_idx(start)

        begin_in = len(self.panel_vertices)
        end_in = begin_in + len(edge_in_vertices)  # exclusive

        for v in edge_in_vertices:
            self.panel_vertices.append(v)

        end_index = self._get_exist_idx(end)

        edge.set_vertex_range(start_index, begin_in, end_in, end_index)


    def sort_edges_by_stitchid(self):
        """
        This function sorts the panel's edges by their edge_id (stitch edges first) and
        returns them as well as the number of edges that are part of a stitch.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
        Output:
            * n_stitch_edges (int): number of panel edges that are part of a stitch
            * sorted edges (list): list containing the stitch_edges first and then the non-stitch edges
        """
        edges = self.edges
        stitch_edges = []
        non_stitch_edges = []
        for edge_id, edge in enumerate(edges):
            if edge.stitch_ref is not None:
                stitch_edges.append((edge_id,edge))
            else:
                non_stitch_edges.append((edge_id,edge))
        n_stitch_edges = len(stitch_edges)
        sorted_edges = stitch_edges + non_stitch_edges
        return n_stitch_edges, sorted_edges


    def gen_panel_mesh(self, mesh_resolution, plot=False, check=False): 
        """
        This function generates the vertices inside the panel using the vertices along the edges.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
            * plot (bool): Indicates if triangle mesh should be plotted
            * check (bool): Indicates if point coordiantes should be compared
        Output:
            * keep_pts_f (list): Vertices inside the panel (without newly inserted boundary vertices)
            * f (list): Triangle faces of the panel
        """
        points = self.panel_vertices
        len_points = len(points)
        edge_verts_ids = tri_utils.get_edge_vert_ids(self.edges)


        cdt_mesh = tri_utils.Mesh_2_Constrained_Delaunay_triangulation_2()
        cdt_points_mesh = tri_utils.create_cdt_points(cdt_mesh,points)
        tri_utils.cdt_insert_constraints(cdt_mesh,cdt_points_mesh,edge_verts_ids)

        #Meshing the triangulation with default shape criterion; i.e. sqrt(1/(4 * 0.125)) = sqrt(2)
        tri_utils.CGAL_Mesh_2.refine_Delaunay_mesh_2(cdt_mesh,
                                           tri_utils.Delaunay_mesh_size_criteria_2(0.125, 1.43 * mesh_resolution)) #1.475

        if plot:
            # Mark faces that are inside the domain
            face_info = tri_utils.mark_domain(cdt_mesh)
            tri_utils.plot_triangulation(cdt_mesh, face_info)

        keep_pts_f = tri_utils.get_keep_vertices(cdt_mesh, len_points)

        # Triangulate mesh without newly inserted boundary points
        cdt = tri_utils.Constrained_Delaunay_triangulation_2()
        cdt_points = tri_utils.create_cdt_points(cdt, keep_pts_f)
        new_points = tri_utils.cdt_insert_constraints(cdt, cdt_points, edge_verts_ids)

        # Faces without accidentially inserted points -- again!
        # NOTE: point insertion might be a sign of degenerate triangles. 
        # But instead a separate check was added
        f = list(tri_utils.get_face_v_ids(cdt, keep_pts_f, new_points, check=check, plot=plot))

        #Store
        self.panel_vertices = keep_pts_f
        self.panel_faces = f

    def is_manifold(self, tol=1e-2):
        return tri_utils.is_manifold(
            np.asarray(self.panel_faces), 
            np.asarray(self.panel_vertices),
            tol=tol
        )

    def save_panel_mesh_obj(self, folder_path: Path):
        """
        This function creates an obj file of the generated panel mesh and stores it to folder_path
        Assumes that panel meshes have already been generated.
        Input:
            * self (Panel object): Instance of Panel class from which the function is called
        """
        folder_path.mkdir(exist_ok=True, parents=True)
        filepath = folder_path / (self.panel_name + ".obj")

        v = self.rot_trans_panel(self.panel_vertices)
        f = np.array(self.panel_faces)

        igl.write_triangle_mesh(str(filepath), v, f)

class Edge:
    """
    Represents an edge of a panel:
        Input:
            * edge: panel information
            * vertices: panel corner vertices
    """
    def __init__(self, edge, vertices, mesh_resolution):
        self.endpoints = vertices[edge['endpoints']]
        self.stitch_ref = None
        self.n_edge_verts = -1
        self.curve = None
        self.init_curve(edge, mesh_resolution)
        self.vertex_range = []
        self.label = edge['label'] if 'label' in edge else ''


    def init_curve(self, edge, mesh_resolution):
        """
        Initialize curve object (svgpathtools) and set the number
        of vertices on the edge (n_edge_verts) depending
        on the mesh_resolution (= 1.0 => Vertices are spread with distance ~1.0 cm)
        Input:
            * self (Edge object): Instance of Edge class from which the function is called
            * edge (dict): edge information
        """
        start, end = self.endpoints

        if 'curvature' in edge:
            if isinstance(edge['curvature'], list) or edge['curvature']['type'] == 'quadratic':  # NOTE: placeholder for old curves for backward compatibility
                control_scale = edge['curvature'] if isinstance(edge['curvature'], list) else edge['curvature']['params'][0] #maya _flip_y
                control_point = pat_utils.rel_to_abs_2d(start, end, control_scale)
                self.curve = svgpath.QuadraticBezier(*pat_utils.list_to_c([start, control_point, end]))

            elif edge['curvature']['type'] == 'circle':  # Assuming circle
                # https://svgwrite.readthedocs.io/en/latest/classes/path.html#svgwrite.path.Path.push_arc

                radius, large_arc, right = edge['curvature']['params']

                self.curve = svgpath.Arc(
                    pat_utils.list_to_c(start), radius + 1j * radius,
                    rotation=0,
                    large_arc=large_arc,
                    sweep=right, #maya: not right
                    end=pat_utils.list_to_c(end)
                )

            elif edge['curvature']['type'] == 'cubic':
                cps = []
                for p in edge['curvature']['params']:
                    control_scale = p #maya: self.flip_y(p)
                    control_point = pat_utils.rel_to_abs_2d(start, end, control_scale)
                    cps.append(control_point)

                self.curve = svgpath.CubicBezier(*pat_utils.list_to_c([start, *cps, end]))

            else:
                raise NotImplementedError(
                    f'{self.__class__.__name__}::{self.name}::Unknown curvature type {edge["curvature"]["type"]}')

        else:
            self.curve = svgpath.Line(*pat_utils.list_to_c([start, end]))

        edgelength = self.curve.length()
        res = mesh_resolution
        n_edge_verts = math.ceil(edgelength / res) + 1

        self.n_edge_verts = n_edge_verts

        if n_edge_verts == 2 and res > 1.0:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Detected edge represented only by two vertices..'
                  'mesh resolution might be too low. resolution = {}, edge length = {}'.format(res, edgelength))


    def set_vertex_range(self, start_idx, begin_in, end_in, end_idx):
        """
        This function sets the vertex range of the current edge in the context of a panel.
        The vertex range contains the indices into panel_vertices, defining the edge vertices with
        respect to the panel_vertices.
        Input:
            * self (Edge object): Instance of Edge class from which the function is called
            * start_idx (int): Index of edge.start into panel_vertices
            * begin_in (int): Index of 2nd edge vertex into panel_vertices
            * end_in (int): Index + 1 of second to last edge vertex into panel_vertices
            * end_idx (int): Index of edge.end into panel_vertices
        """
        self.vertex_range = [start_idx] + list(range(begin_in, end_in)) + [end_idx]


    def as_curve(self, absolute=True):
        """
            Returns curve as a svgpath curve object.
            Converting on the fly as exact vertex location might have been updated since
            the creation of the edge
        Input:
            * self (Edge object): Instance of Edge class from which the function is called
            * absolute (bool): True if correct start and end edge vertices are processed
            else use start = [0,0] and end = [1,0]

        Output:
            * svgpath path object: either correct curve or approximation
        """

        if absolute:
            # Return correct curve
            return self.curve

        cp = [pat_utils.c_to_np(c) for c in self.curve.bpoints()[1:-1]]
        nodes = np.vstack(([0, 0], cp, [1, 0]))
        params = nodes[:, 0] + 1j * nodes[:, 1]
        return svgpath.QuadraticBezier(*params) if len(cp) < 2 else svgpath.CubicBezier(*params)


    def linearize(self, panel):
        """
        Returns the current edge (self) as a sequence of lines
        Input:
            * self (Edge object): Instance of Edge class from which the function is called

        Output:
            * (numpy ndarray): a list of vertices (start and end vertices of corresponding line)
            characterizing the current edge (self)
        """
        if isinstance(self.curve, svgpath.Line):
            return [self.endpoints]
        else:
            v_range = self.vertex_range
            edge_vertices = np.array(panel.panel_vertices)[v_range]
            edge_seq = []
            for i in range(len(edge_vertices) - 1):
                pair = [edge_vertices[i], edge_vertices[i + 1]]
                edge_seq.append(pair)
            return edge_seq

class Seam:
    def __init__(self, 
                 panel_1_name, edge_1, 
                 panel_2_name, edge_2,
                 label=None,
                 n_verts=None,
                 swap=True
                 ):
        """
            Representation of a seam in a box mesh
            Input: 
                * panel_1_name, edge_1, panel_2_name, edge_2 -- panel edge objects and corresponding
                    panel names for two edges connected by the stitch
                * label -- label to assing to the seam on serialisaton (default: None)
                * n_verts -- number of mesh vertices sampled for the seam (default: None, not samples)
                * swap -- define the edge swap for the edge pair. Default: True --
                    swapped -- the end of one panel edge connects to the start vertex
                    of the other panel edge
        """
        self.panel_1, self.panel_2 = panel_1_name, panel_2_name
        self.edge_1, self.edge_2 = edge_1, edge_2

        self.label = label

        # NOTE: default connection of stitches is edge1 end-> edge2 start 
        # following manifold condition 
        # => stitch right side to the right side of the fabric pieces
        self.swap = swap   # Default swap state connects right side to the right side of fabric

        self.n_verts = n_verts   # Number of mesh vertices

# !SECTION

# SECTION Box Mesh
class BoxMesh(wrappers.VisPattern):
    """
    Extends a pattern specification in custom JSON format to generate a box mesh from the pattern
        Input:
            * pattern_file: pattern template in custom JSON format
    """
    def __init__(self, path, res=1.0):
        super(BoxMesh, self).__init__(path)
        self.mesh_resolution = res #Vertices are spread with distance ~mesh_resolution cm
        self.loaded = False
        self.panels: Dict[str, Panel] = {}
        self.stitches: List[Seam] = [] 
        self.panelNames = self.panel_order()
        self.vertices = []
        self.faces = []
        self.orig_lens = {}

        self.verts_loc_glob = {}
        self.verts_glob_loc = []
        self.stitch_segmentation = []
        self.vertex_normals = []
        self.faces_with_texture = []
        self.vertex_texture = []
        self.vertex_labels = {}   # Additional vertex labels coming from panel edges' labels

    # SECTION -- Top level 
    def load(self):
        """
        Loads all relevant functions and prints their time consumptions
        """
        if self.is_self_intersecting(): 
            print(f'{self.__class__.__name__}::WARNING::{self.name}::Provided pattern has self-intersecting panels. Simulation might crash')

        self.load_panels()
        self.gen_panel_meshes()

        # NOTE: Collapse stitch vertices and store to self.vertices as well as their stitch_id to self.stitch_segmentation
        self.collapse_stitch_vertices()

        self.finalise_mesh()
        self.loaded = True

    def load_panels(self):
        """
        For each panel of the pattern create a panel object and load stitching info + set number of
        stitching edge vertices
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        """
        all_panels = self.pattern['panels']
        for panel_name in self.panelNames:
            panel = Panel(all_panels[panel_name], panel_name, self.mesh_resolution)
            self.panels[panel_name] = panel

        #Load stitching info
        self.read_stitches()

    # !SECTION
    # SECTION -- Stitch references in panels
    def _get_stitch_edge_info(self, stitch_id, side_id) -> Tuple[str, int, Edge]:
        """
        This function returns the edge defined by stitch_id and side_id
        as well as its edge id and the panel name of the panel the edge is part of
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * stitch_id (int)
            * side_id (int)
        Output:
            * panel_name (str): panel name of edge with stitch_id and side_id
            * edge_id (int): id of edge with stitch_id and side_id
            * edge (Edge object): Edge object of edge with stitch_id and side_id
        """
        panel_name = self.pattern['stitches'][stitch_id][side_id]['panel']
        edge_id = self.pattern['stitches'][stitch_id][side_id]['edge']
        ret_panel = self.panels[panel_name]
        try:
            edge = ret_panel.edges[edge_id]
        except BaseException:
            print(f'{self.__class__.__name__}::ERROR::{self.name}::Provided pattern'
                  f' fails for stitch id {stitch_id} and {[panel_name,edge_id]}')
            raise PatternLoadingError(
                f'{self.__class__.__name__}::{self.name}::ERROR::Provided pattern'
                f' fails for stitch id {stitch_id} and {[panel_name,edge_id]}')
        else:
            return panel_name, edge_id, edge

    def read_stitches(self):
        """
        * Load the stitching information from the spec
        * Determine the number of mesh vertices to be generated on edges, s.t. they match in the stitches
        """
        multi_stitches_check = []
        if 'stitches' in self.pattern:
            for stitch_id in range(len(self.pattern['stitches'])):
                stitch_spec = self.pattern['stitches'][stitch_id]
                panel_name_0, edge_id0, edge0 = self._get_stitch_edge_info(stitch_id, 0)
                panel_name_1, edge_id1, edge1 = self._get_stitch_edge_info(stitch_id, 1)

                stitch = Seam(panel_name_0, edge_id0, panel_name_1, edge_id1)
                stitch.swap = not (len(stitch_spec) == 3 and 'right_wrong' == stitch_spec[-1])
                self.stitches.append(stitch)

                edge0.stitch_ref, edge1.stitch_ref = stitch, stitch

                n_0, n_1 = edge0.n_edge_verts, edge1.n_edge_verts
                # Assign n of longer edge
                n = n_0 if edge0.curve.length() > edge1.curve.length() else n_1
                edge0.n_edge_verts = n
                edge1.n_edge_verts = n
                stitch.n_verts = n
                #---
                multi_edge = [(p,e) for (p,e) in [(panel_name_0, edge_id0), (panel_name_1, edge_id1)]
                              if (p,e) in multi_stitches_check]
                if multi_edge:
                    raise MultiStitchingError(
                        f'{self.__class__.__name__}::{self.name}::ERROR::Multi stitching'
                        f' detected at stitch id {stitch_id} from {multi_edge}')
                else:
                    multi_stitches_check.append((panel_name_0, edge_id0))
                    multi_stitches_check.append((panel_name_1, edge_id1))

                # Propagate Edge labeling
                if edge0.label or edge1.label:
                    if edge0.label and edge1.label and edge0.label != edge1.label:   # Sanity check
                        raise ValueError(
                            f'{self.__class__.__name__}::{self.name}::ERROR::Edge labels '
                            f'in stitch do not match: {edge0.label} and {edge1.label}')
                    stitch.label = edge0.label if edge0.label else edge1.label
        else:
            print(f'{self.__class__.__name__}::INFO::No stitching information provided')

    # !SECTION
    # SECTION -- generate per-panel meshes
    def _get_edge_in_verts(self, edge, plot=False):
        """
        This function generates the pre-defined number of vertices for each edge
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * edge (Edge object): Instance of Edge class for which the vertices are generated
            * panelname (str): Name of the panel to which edge belongs to; only used if plot = True
            * edge_id (int): Edge identifier; only used if plot = True
            * plot (bool): If plot == True, plots edge vertices
        Output:
            * edge_in_vertices (list): n_edge_verts equally spread vertices along edge
        """
        n = edge.n_edge_verts

        edge_in_vertices = []
        t_vals = np.linspace(0, 1, n)

        if isinstance(edge.curve, svgpath.QuadraticBezier) or isinstance(edge.curve, svgpath.CubicBezier):
             # to achieve equal spread along bezier curve
            curve_lengths = np.linspace(0,1,n) * edge.curve.length()
            t_vals = [edge.curve.ilength(c_len) for c_len in curve_lengths]

        ts = t_vals[1:(n - 1)]  # remove start and end from "inside vertices"
        if isinstance(edge.curve, svgpath.Arc):
            for t in ts:
                p = pat_utils.c_to_np(edge.curve.point(t))
                edge_in_vertices.append(p)
        else:
            points = edge.curve.points(ts)  # faster than .point(t) but unavailable for Arc
            edge_in_vertices = [pat_utils.c_to_np(p) for p in points]


        if plot:
            c_type = "circle"
            if isinstance(edge.curve, svgpath.QuadraticBezier) or isinstance(edge.curve, svgpath.CubicBezier):
                c_type = "bezier"
            elif isinstance(edge.curve, svgpath.Line):
                c_type = "linear"

            show_verts = np.array([edge.endpoints[0]] +list(edge_in_vertices) + [edge.endpoints[1]])

            lis = show_verts.T #np.array(edge_in_vertices).T
            x,y = lis
            x = list(x)
            y = list(y)
            plt.scatter(x, y)

            plt.axis('square')
            plt.title(c_type)

            for i in range(len(show_verts)):
                plt.annotate(i, (x[i], y[i]), textcoords="offset points", xytext=(0, 10), ha='center')

            plt.show()

        return edge_in_vertices

    def gen_panel_meshes(self):
        """
        For each Panel:
            * For each edge generate its edge vertices and store them in panel.panel_vertices.
              Further, store "start", "inside-edge", and "end" indices for each edge vertex in edge.vertex_range
            * Generate vertices inside the panel and its triangles using CGAL and store them in panel.panel_vertices
              and panel.panel_triangles, respectively.
        Input:
        * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        """
        for panelname in self.panelNames:
            panel = self.panels[panelname]

            #Sort panel.edges by stitch id
            n_stitch_edges, sorted_edges = panel.sort_edges_by_stitchid()

            for i,(edge_id,edge) in enumerate(sorted_edges):
                #Get vertices for edge (without start, end)
                edge_in_vertices = self._get_edge_in_verts(edge, plot = False)

                #Store start, inside, and end vertices to Panel.panel_vertices and indices to edge.sitch_range
                panel.store_edge_verts(edge, edge_in_vertices)

                if i == n_stitch_edges - 1:
                    panel.n_stitches = len(panel.panel_vertices)# until now we only have stitch vertices in Panel.panel_vertices

            #Set panel norm
            panel.set_panel_norm()
            #Generate panel mesh and store them in panel.panel_vertices and panel.panel_faces
            panel.gen_panel_mesh(self.mesh_resolution)

            # Sanity check 
            if not panel.is_manifold():
                raise DegenerateTrianglesError(
                    f'{self.__class__.__name__}::ERROR::{self.name}::{panel.panel_name}:'
                    ':panel contains degenerate triangles'
                )

    # !SECTION
    # SECTION -- Merge mesh vertices in stitches
    def _swap_stitch_ranges(self, stitch:Seam):
        """
        This function returns the stitch_ranges of stitched edges in the correct order,
        so that the correct edge vertices are stitched together.
        Input:
            * stitch -- desired stitch to be updated
        Output:
        * stitch_range_1 (list): Correctly ordered indices for stitch.edge_1 in stitch.panel_1
        * stitch_range_2 (list): Correctly ordered indices into stitch.edge_2 in stitch.panel_2
        """
        panel1, panel2 = self.panels[stitch.panel_1], self.panels[stitch.panel_2]

        stitch_range_1 = panel1.edges[stitch.edge_1].vertex_range
        stitch_range_2 = panel2.edges[stitch.edge_2].vertex_range

        # Force existing swap
        if stitch.swap:
            stitch_range_1 = stitch_range_1[::-1]

        return stitch_range_1, stitch_range_2

    def _stitch_same_loc_vertex(self, panel1, loc_id1, glob_idx, stitch_id):
        """
        This function stitches two vertices together which are exactly the same local vertex and
        have not participated in a stitch so far.
        To this end, self.verts_loc_glob, self.verts_glob_loc, self.vertices, and
        self.stitch_segmentation are changed accordingly.
        Input:
        * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        * panel1 (Panel object): Panel object participating in stitch
        * loc_id1 (int): Local identifier of a vertex into panel1.panel_vertices that is stitched together with itself
        * glob_idx (int): Global index of vertex that is stitched together with itself
        * stitch_id (int): Stitch identifier indicating which stitch is currently performed
        """
        p1_name = panel1.panel_name
        self.verts_loc_glob[(p1_name, loc_id1)] = glob_idx
        self.verts_glob_loc.append([(p1_name, loc_id1)])
        v_2D = panel1.panel_vertices[loc_id1]
        self.vertices.append(panel1.rot_trans_vertex(v_2D))
        self.stitch_segmentation.append(["stitch_" + str(stitch_id)])

    def _stitch_two_diff_existent_glob_verts(self, glob1, glob2, glob_idx, stitch_id):
        """
        This function stitches two vertices together where both have already participated in a stitch.
        To this end, self.verts_loc_glob, self.verts_glob_loc, self.vertices, and
        self.stitch_segmentation are changed accordingly.
        Input:
        * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        * glob1 (int): Global identifier of first stitch vertex into self.vertices
        * glob2 (int): Global identifier of second stitch vertex into self.vertices
        * glob_idx (int): Current number of vertices stored in self.vertices
        * stitch_id (int): Stitch identifier indicating which stitch is currently performed
        """
        glob_min = glob1 if glob1 < glob2 else glob2
        glob_max = glob1 if glob1 > glob2 else glob2

        panels_locids = self.verts_glob_loc[glob_max]
        for p_name, loc_id in panels_locids:
            self.verts_loc_glob[(p_name, loc_id)] = glob_min

        repl_glob_ids = list(range(glob_max + 1, glob_idx))
        panel_locids_above = np.array(self.verts_glob_loc, dtype=object)[repl_glob_ids]
        for p_id in panel_locids_above:
            for p_name, loc_id in p_id:
                self.verts_loc_glob[(p_name, loc_id)] -= 1

        curr_glob_v1 = self.vertices[glob_min]
        curr_glob_v2 = self.vertices[glob_max]
        self.vertices[glob_min] = np.mean([curr_glob_v1, curr_glob_v2], axis=0)

        set_verts_glob_loc = set(self.verts_glob_loc[glob_min] + self.verts_glob_loc[glob_max])
        self.verts_glob_loc[glob_min] = list(set_verts_glob_loc)
        del self.verts_glob_loc[glob_max]
        del self.vertices[glob_max]

        copy_stitch_ids = self.stitch_segmentation[glob_max]
        self.stitch_segmentation[glob_min] += copy_stitch_ids + ["stitch_" + str(stitch_id)]
        del self.stitch_segmentation[glob_max]

    def _stitch_one_existent_glob_vert(self, panel_glob, panel_not_glob, loc_id_glob, loc_id_not_glob, stitch_id):
        """
        This function stitches two vertices together where only one of them has already participated in a stitch.
        To this end, self.verts_loc_glob, self.verts_glob_loc, self.vertices, and
        self.stitch_segmentation are changed accordingly.
        Input:
        * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        * panel_glob (Panel object): Panel object referenced by vertex that has already participated in a stitch
        * panel_not glob (Panel object): Panel object referenced by vertex that has not yet participated in a stitch
        * loc_id_glob (int): Local identifier of a stitch vertex into panel_glob.panel_vertices. This vertex has 
        already participated in a stitch.
        loc_id_not_glob (int): Local identifier of a stitch vertex into panel_not_glob.panel_vertices. This vertex 
        has not participated in a stitch so far.
        * stitch_id (int): Stitch identifier indicating which stitch is currently performed
        """
        panel_name_glob = panel_glob.panel_name
        panel_name_not_glob = panel_not_glob.panel_name

        glob = self.verts_loc_glob[(panel_name_glob, loc_id_glob)]
        self.verts_loc_glob[(panel_name_not_glob, loc_id_not_glob)] = glob
        self.verts_glob_loc[glob].append((panel_name_not_glob, loc_id_not_glob))
        v_2D = panel_not_glob.panel_vertices[loc_id_not_glob]
        v_3D = panel_not_glob.rot_trans_vertex(v_2D)
        curr_glob_v = self.vertices[glob]
        self.vertices[glob] = np.mean([v_3D, curr_glob_v], axis=0)
        self.stitch_segmentation[glob].append("stitch_" + str(stitch_id))

    def _stitch_none_existent_glob_verts(self, panel1, panel2, loc_id1, loc_id2, glob_idx, stitch_id):
        """
        This function stitches two vertices together where both of them have not yet participated in a stitch.
        To this end, self.verts_loc_glob, self.verts_glob_loc, self.vertices, and
        self.stitch_segmentation are changed accordingly.
        Input:
        * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        * panel1 (Panel object): Panel object referenced by the first stitch vertex
        * panel2 (Panel object): Panel object referenced by the second stitch vertex
        * loc_id1 (int): Local identifier of the first stitch vertex into panel1.panel_vertices
        * loc_id2 (int): Local identifier of the second stitch vertex into panel2.panel_vertices
        * stitch_id (int): Stitch identifier indicating which stitch is currently performed
        """
        p1_name = panel1.panel_name
        p2_name = panel2.panel_name
        self.verts_loc_glob[(p1_name, loc_id1)] = glob_idx
        self.verts_loc_glob[(p2_name, loc_id2)] = glob_idx
        self.verts_glob_loc.append([(p1_name, loc_id1), (p2_name, loc_id2)])
        v1_2D = panel1.panel_vertices[loc_id1]
        v1_3D = panel1.rot_trans_vertex(v1_2D)
        v2_2D = panel2.panel_vertices[loc_id2]
        v2_3D = panel2.rot_trans_vertex(v2_2D)
        self.vertices.append(np.mean([v1_3D, v2_3D], axis=0))
        self.stitch_segmentation.append(["stitch_" + str(stitch_id)])

    def _stitch_vertices(self):
        """
        This function:
            * Determines if the stitch_range of one edge has to be reversed
              (so that edges which are stitched together have the same direction)
            * Computes stitch vertices by taking the mean of corresponding 3D panel vertex pairs
            * Stores the local to global vertex indices relationship in self.verts_loc_glob
            * Stores the glboal to local vertex indices relationship in self.verts_glob_loc
            * Stores the 3D stitch vertices into self.vertices
            * Stores the stitch_ids to the self.stitch_segmentation list

        Output:
        * same_panel_stitching_dict (dict): Dictionary storying the local vertex indices to which a local vertex
        of the same panel is stitched together, i.e.,
        (panel_name, local_vertex_id) = [local vertex ids of same panel stiched together with local_vertex_id)
        """
        # Collapse stitch vertices
        same_panel_stitching_dict = {} #Store stichings of same panel (panelname,loc_id) -> loc_id
        glob_idx = 0
        self.verts_loc_glob = {}
        self.verts_glob_loc = []
        self.vertices = []
        self.stitch_segmentation = []
        
        for stitch_id, stitch in enumerate(self.stitches):
            panel1, panel2 = self.panels[stitch.panel_1], self.panels[stitch.panel_2]

            stitch_range_1, stitch_range_2 = self._swap_stitch_ranges(stitch)

            # Record same panel connections
            if stitch.panel_1 == stitch.panel_2:
                s1, e1 = stitch_range_1[0], stitch_range_1[-1]
                s2, e2 = stitch_range_2[0], stitch_range_2[-1]
                s_min, s_max = min(s1, s2), max(s1, s2)
                e_min, e_max = min(e1, e2), max(e1, e2)
                same_panel_stitching_dict.setdefault((stitch.panel_1, s_min), []).append(s_max)
                same_panel_stitching_dict.setdefault((stitch.panel_2, e_min), []).append(e_max)

            # Perform matching
            for loc_id1, loc_id2 in zip(stitch_range_1, stitch_range_2):
                if stitch.panel_1 == stitch.panel_2 and loc_id1 == loc_id2: #same vertex
                    if (stitch.panel_1, loc_id1) not in self.verts_loc_glob.keys():
                        self._stitch_same_loc_vertex(panel1, loc_id1, glob_idx, stitch_id)
                        glob_idx += 1
                    else:
                        glob_id = self.verts_loc_glob[(stitch.panel_1, loc_id1)]
                        self.stitch_segmentation[glob_id].append("stitch_" + str(stitch_id))
                else:
                    v1_glob_exists = (stitch.panel_1, loc_id1) in self.verts_loc_glob.keys()
                    v2_glob_exists = (stitch.panel_2, loc_id2) in self.verts_loc_glob.keys()
                    if v1_glob_exists and v2_glob_exists: #both exist
                        glob1 = self.verts_loc_glob[(stitch.panel_1, loc_id1)]
                        glob2 = self.verts_loc_glob[(stitch.panel_2, loc_id2)]
                        if glob1 != glob2:
                            self._stitch_two_diff_existent_glob_verts(glob1, glob2, glob_idx, stitch_id)
                            glob_idx -= 1
                    elif v1_glob_exists:
                        self._stitch_one_existent_glob_vert(panel1, panel2, loc_id1, loc_id2, stitch_id)
                    elif v2_glob_exists:
                        self._stitch_one_existent_glob_vert(panel2, panel1, loc_id2, loc_id1, stitch_id)
                    else: #none exist
                        self._stitch_none_existent_glob_verts(panel1, panel2, loc_id1, loc_id2, glob_idx, stitch_id)
                        glob_idx += 1

        return same_panel_stitching_dict

    # !SECTION
    # SECTION Stitching -- min validity checks
    def check_local_vertices_stitching(self, dic, panel_name, loc_ids):
        """
        This function checks for valid "same panel stitching" based on vertices given as a set of
        local vertex ids and a dictionary with "same panel stitching" information.

        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called.
            * dic (dict): same_panel_stitching_dict, dictionary storing the local vertex indices to which a
            local vertex of the same panel is stitched together
            * loc_ids (list): List of vertex ids representing vertices that are stitched into one global vertex
                in the same panel and are needed to be checked for validity.
            * panel_name (str): Panel name used to identify the panel.


        Output:
            * True if any local vertex (defined by loc_ids) is stitched together with at least one other
            local vertex but it happens outside of the valid panel stitch; otherwise, False.
        """
        # Checking all the pairs: 
        # same id -> same id is a connection in the dart stitch (at the tip)
        for i in loc_ids:
            invalid = True
            # NOTE: there could be some invalid pairings, but as long as we find
            # a valid one for each loc_ids vertex, we are good.
            for j in loc_ids:
                min_id = min(i, j)
                max_id = max(i, j)

                if ((panel_name, min_id) in dic.keys()) and (max_id in dic[(panel_name, min_id)]):
                    # i is stitched to j in a valid same-panel stitch
                    # => i is supposed to be part of current global vertex in question
                    invalid = False  
                    break 
            if invalid:
                # Cannot find a intra-panel stitch that connects i 
                # into this global vertex -> incorrect
                return True
        return False

    def _group_same_panel_stiches(self, inner_list):
        """
         This function groups together stitched vertices that belong to the same panel.

        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called.
            * inner_list (list): List of tuples representing same panel stitching information, 
            where each tuple contains the panel name and a vertex id.

        Output:
            * final_result (list): List of tuples where the first element is the panel name, and the second
            element is a list of vertex IDs that are stitched together with another vertex of that panel.
        """

        result_dict = {}

        for name, value in inner_list:
            if name in result_dict:
                result_dict[name].append(value)
            else:
                result_dict[name] = [value]

        # Filter only the panels with more than one value
        final_result = [(name, values) for name, values in result_dict.items() if len(values) > 1]

        return final_result

    def _check_same_panel_stitching(self, dic, global_ids):
        """
            This function checks for stitching of local vertices within the same panel based on a given dictionary
            containing "same panel stitching" information and global vertex IDs representing the end vertices of
            two edges that are stitched together.

            Input:
                * self (BoxMesh object): Instance of BoxMesh class from which the function is called.
                * dic (dict): same_panel_stitching_dict, dictionary storing the local vertex indices to which a
                local vertex of the same panel is stitched together
                * global_ids (list): global vertex IDs representing the end vertices of two edges that
                are stitched together

            Output:
                * Returns True if stitching is incorrect: there are local vertices associated with 
                the provided global IDs that are stitched together within the same panel; 
                otherwise, returns False.
        """
        for g_id in global_ids:
            l_old = self.verts_glob_loc[g_id]  # All local verts corresponding to g_id
            # Groups by panels, if there are multiple vertices from the same panel
            l = self._group_same_panel_stiches(l_old)
            if not dic and l:
                return True
            for panel_name, loc_ids in l:
                if self.check_local_vertices_stitching(dic, panel_name, loc_ids):
                    return True

        return False

    def _valid_stitch_front_end(self, stitch: Seam):
        """
            This function checks if any front and end vertices of the two edges taking part in a stitch
            have been stitched together.

            Input:
                * stitch object

            Output:
                * Returns False if any front and end vertices of the two edges taking part in a stitch
                have been stitched together; otherwise, returns True.

        """
        panel1 = self.panels[stitch.panel_1]
        panel2 = self.panels[stitch.panel_2]

        edge1 = panel1.edges[stitch.edge_1]
        edge2 = panel2.edges[stitch.edge_2]

        s1_glob = self.verts_loc_glob[(stitch.panel_1, edge1.vertex_range[0])]
        e1_glob = self.verts_loc_glob[(stitch.panel_1, edge1.vertex_range[-1])]
        s2_glob = self.verts_loc_glob[(stitch.panel_2, edge2.vertex_range[0])]
        e2_glob = self.verts_loc_glob[(stitch.panel_2, edge2.vertex_range[-1])]

        # Check if start and end was collapsed together
        if s1_glob == e1_glob or s2_glob == e2_glob:
            return False
        else:
            return True

    def _valid_stitch_same_panel(self, stitch:Seam, same_panel_stitching_dict):
        """
            This function examines whether the front and end vertices of two edges participating in a
            stitching operation have been improperly stitched together with another vertex from the same panel.

            Input:
                * self (BoxMesh object): Instance of BoxMesh class from which the function is called.
                * p1_name (str): panel name to which the frist stitch edge belongs.
                * edge_id1 (int): edge id of first stitch edge
                * p2_name (str): panel name to which the second stitch edge belongs.
                * edge_id2 (int): edge id of second stitch edge
                * same_panel_stitching_dict (dict): dictionary storing the local vertex indices to which a
                local vertex of the same panel is stitched together


            Output:
                * Returns False if any front and end vertices of two edges participating in a
                stitching operation have been improperly stitched together with another vertex from the same panel;
                otherwise, returns True.

        """

        panel1 = self.panels[stitch.panel_1]
        panel2 = self.panels[stitch.panel_2]

        edge1 = panel1.edges[stitch.edge_1]
        edge2 = panel2.edges[stitch.edge_2]

        s1_glob = self.verts_loc_glob[(stitch.panel_1, edge1.vertex_range[0])]
        e1_glob = self.verts_loc_glob[(stitch.panel_1, edge1.vertex_range[-1])]
        s2_glob = self.verts_loc_glob[(stitch.panel_2, edge2.vertex_range[0])]
        e2_glob = self.verts_loc_glob[(stitch.panel_2, edge2.vertex_range[-1])]

        return not self._check_same_panel_stitching(
            same_panel_stitching_dict, [s1_glob, e1_glob, s2_glob, e2_glob])

    def _is_stitching_valid(self, same_panel_stitching_dict, front_end_only=False):
        """Check validity of a current stitching"""
        stitch_ids_invalid = []
        for stitch_id, stitch in enumerate(self.stitches):
            front_end_valid = self._valid_stitch_front_end(stitch)
            same_panel_valid = self._valid_stitch_same_panel(stitch, same_panel_stitching_dict)

            if front_end_only:
                if not front_end_valid:
                    stitch_ids_invalid.append(stitch_id)
            else:
                if not front_end_valid or not same_panel_valid:
                    stitch_ids_invalid.append(stitch_id)

        valid = len(stitch_ids_invalid) == 0

        return valid, stitch_ids_invalid
    # !SECTION
    # SECTION -- Stitch collapsing init
    def collapse_stitch_vertices(self):
        """
        This function performs the stitching and checks if any anomalies can be detected
        Input:
        * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        """

        # NOTE: don't need this
        # Try the stitching -- performs global vertex matching
        same_panel_stitching_dict = self._stitch_vertices()

        # Check stitches validity: edge collapse (start==end)
        # NOTE: Separating checks by error type to reduce number of invalid stitch orientations to process
        # in each case
        valid, _ = self._is_stitching_valid(
            same_panel_stitching_dict, 
            front_end_only=False)
        if not valid:
            print(f'{self.__class__.__name__}::{self.name}::ERROR::Invalid stitching. Unable to fix')
            raise StitchingError()

    # !SECTION
    # SECTION -- Mesh finalization
    def _get_glob_ids(self, panel, face):
        """
        This function returns the global indices of the face vertices.
        Input
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * panel_name (str): The panel name of the panel the face is from
            * face (ndarray): Contains the local indices of the face vertices into panel.panel_faces
            * len_B_verts (int): Current number of vertices stored in self.vertices
            * n_stitches_panel (int): Number of stitch vertices of the whole panel
        Output:
            * glob_indices (list): Global indices of face vertices into self.vertices
        """
        glob_indices = []
        n_stitches_panel = panel.n_stitches
        for loc_id in face:
            if loc_id < n_stitches_panel:
                glob_indices.append(self.verts_loc_glob[(panel.panel_name, loc_id)])
            else:
                glob_indices.append(loc_id + panel.glob_offset - n_stitches_panel)

        return glob_indices

    def calc_norm(self, a, b, c):
        """
        This function calculates the norm based on the three points a, b, and c.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * a (ndarray): first point taking part in norm calculation
            * b (ndarray): second point taking part in norm calculation
            * c (ndarray): third point taking part in norm calculation
        Output:
            * n_normalized (bool): norm(a,b,c) with length 1
        """
        # Calculate the vectors AB and AC
        AB = np.array(b - a)
        AC = np.array(c - a)

        # Calculate the cross product of AB and AC
        n = np.cross(AB, AC)
        n_normalized = n / np.linalg.norm(n)

        return n_normalized

    def _check_norm_local(self, idx_a, idx_b, idx_c, panel_norm, v_3D):
        """
        This function checks if the norm defined by the three vertices a,b, and c equals panel_norm.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * idx_a (int): Index of the first vertex into v_3D
            * idx_b (int): Index of the second vertex into v_3D
            * idx_c (int): Index of the third vertex into v_3D
            * panel_norm (list): The norm of a panel to which norm(a,b,c) is compared to
            * v_3D (list): The 3D vertices of a panel
        Output:
            * same_norm (bool): True if norm(a,b,c) equals panel_norm, else False
        """
        a, b, c = np.array(v_3D)[[idx_a, idx_b, idx_c]]

        n_normalized = self.calc_norm(a, b, c)

        same_norm = np.allclose(n_normalized,panel_norm)
        return same_norm

    def _order_face_vertices(self, panel, v_3D):
        """
        This function orders the face vertices of panel.panel_faces so that the face norms equal the panel's norm.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * panel(Panel object): Panel object whose norm is used for comparison
            * v_3D (list): The 3D vertices of panel.panel_vertices
        """
        # Check first face:
        idxa, idxb, idxc = panel.panel_faces[0]
        if not self._check_norm_local(idxa, idxb, idxc, panel.norm, v_3D):
            faces_array = np.array(panel.panel_faces)
            # Swap the 2nd and 3rd columns
            faces_array[:, [1, 2]] = faces_array[:, [2, 1]]
            panel.panel_faces = list(faces_array)

    def _set_el_within_range(self, low, up, tolerance_factor=0.02):
        """
        This function returns a value between low and up based on the tolerance_factor.
        Input:
            * low (float): lower bound (exclusive)
            * up (float): upper bound (exclusive)
            * tolerance_factor (float): influences how close the GT edge length is to low
        Output:
            * el (float): new GT edge length close to low
        """
        range_distance = up - low
        tol = tolerance_factor * range_distance
        el = low + tol
        return el

    def _get_seam_gt_el(self, el_i, el_j, el_k, id1, id2, stitch_edges_gt):
        """
        This function returns the ground truth length of edges between two stitch vertices.
        It returns the minimum edge length if the triangle inequality (e1 + e2 > e3, e2 + e3 > e1, e1 + e3 > e2),
        is satisfied. Otherwise, it returns the smallest value that maintains the validity of the adjacent triangles
        (if possible).
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * el_i (float): second edge length of stitch edge i
            * el_j (float): edge length of edge j which is part of the same triangle
            * el_k (float): edge length of edge k which is part of the same triangle
            * id1 (int): global vertex id of first edge vertex (vertex is a stitch vertex)
            * id2 (int): global vertex id of second edge vertex (vertex is a stitch vertex)
            * stitch_edges_gt (dict): Dict storing lower bound, upper bound and current edge length of previously
            encountered edge with vertices id1 and id2

        """
        low_old, up_old, el_i_old = stitch_edges_gt[(id1, id2)]
        min_el = min([el_i, el_i_old])
        low = max(low_old, abs(el_j - el_k))
        up = min(up_old, el_j + el_k)
        if low < min_el and min_el < up:
            el = min_el
        elif low < up and min_el < low:
            el = self._set_el_within_range(low,up)
        else:
            # raise ValueError(f"Not possible to set triangle edge of vertices {id1} and {id2}")
            print(f'{self.__class__.__name__}::WARNING::{self.name}::Impossible to set '
                  f' ground truth edge length of vertices {id1} and {id2}. '
                  'Simulation is going to crash')
            return low
        return el

    def _store_to_orig_lens(self, panel, face, f_glob_ids, stitch_edges_gt):
        """
        This function stores the lengths between the local 2D face vertices
        to self.orig_lens in terms of their global indices.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * panel (Panel object): Panel object the face is from
            * face (ndarray): Contains the face vertex indices into panel.panel_vertices
            * f_glob_ids (list): The global indices of the face vertices into self.vertices
        """
        # Sort f_glob_ids and get the corresponding indices
        sorted_indices = sorted(range(3), key=lambda i: f_glob_ids[i])

        # Sort f_glob_ids and face (local ids) based on the sorted indices
        glob_id1, glob_id2, glob_id3 = np.array(f_glob_ids)[sorted_indices]
        f_loc_id_1, f_loc_id_2, f_loc_id_3 = face[sorted_indices]

        v1 = panel.panel_vertices[f_loc_id_1]
        v2 = panel.panel_vertices[f_loc_id_2]
        v3 = panel.panel_vertices[f_loc_id_3]

        el1 = np.linalg.norm(np.array(v2 - v1))
        el2 = np.linalg.norm(np.array(v3 - v2))
        el3 = np.linalg.norm(np.array(v3 - v1))

        e1_exists = (glob_id1,glob_id2) in stitch_edges_gt.keys()
        e2_exists = (glob_id2, glob_id3) in stitch_edges_gt.keys()
        e3_exists = (glob_id1, glob_id3) in stitch_edges_gt.keys()

        low1_old, low2_old, low3_old = None, None, None

        if e1_exists:
            low1_old, up1_old, _ = stitch_edges_gt[glob_id1, glob_id2]
            el1 = self._get_seam_gt_el(el1, el2, el3, glob_id1, glob_id2, stitch_edges_gt)
        self.orig_lens[(glob_id1, glob_id2)] = el1

        if e2_exists:
            low2_old, up2_old, _ = stitch_edges_gt[glob_id2, glob_id3]
            el2 = self._get_seam_gt_el(el2, el1, el3, glob_id2, glob_id3, stitch_edges_gt)
        self.orig_lens[(glob_id2, glob_id3)] = el2

        if e3_exists:
            low3_old, up3_old, _ = stitch_edges_gt[glob_id1, glob_id3]
            el3 = self._get_seam_gt_el(el3, el1, el2, glob_id1, glob_id3, stitch_edges_gt)
        self.orig_lens[(glob_id1, glob_id3)] = el3

        n_stitches = panel.n_stitches
        v1_stitch = f_loc_id_1 < n_stitches
        v2_stitch = f_loc_id_2 < n_stitches
        v3_stitch = f_loc_id_3 < n_stitches

        if v1_stitch and v2_stitch:
            if low1_old:
                stitch_edges_gt[glob_id1, glob_id2] = [max(low1_old, abs(el2 - el3)), min(up1_old, el2 + el3), el1]
            else:
                stitch_edges_gt[glob_id1, glob_id2] = [abs(el2 - el3), el2 + el3, el1]
        if v2_stitch and v3_stitch:
            if low2_old:
                stitch_edges_gt[glob_id2, glob_id3] = [max(low2_old, abs(el1 - el3)), min(up2_old, el1 + el3), el2]
            else:
                stitch_edges_gt[glob_id2, glob_id3] = [abs(el1 - el3), el1 + el3, el2]
        if v1_stitch and v3_stitch:
            if low3_old:
                stitch_edges_gt[glob_id1, glob_id3] = [max(low3_old, abs(el1 - el2)), min(up3_old, el1 + el2), el3]
            else:
                stitch_edges_gt[glob_id1, glob_id3] = [abs(el1 - el2), el1 + el2, el3]

    def get_v_texture(self, panel_vertices):
        """
        Returns the minimum x and y value of panel_vertices
        """
        p_v_arr = np.array(panel_vertices)
        trans = [min(p_v_arr[:,0]), min(p_v_arr[:,1])]
        v_texture = p_v_arr - trans
        return v_texture.tolist()

    def finalise_mesh(self):
        """
        This function finalizes box mesh after stitching has finished:
        * Creates self.faces and self.vertices
        * Creates stitch segmentation
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
        """
        stitch_edges_gt = {}
        #Store orignal length between stitch vertices and their neighbors
        for panelname in self.panelNames:
            panel = self.panels[panelname]
            n_stitches_panel = panel.n_stitches
            len_B_verts = len(self.vertices)
            panel.glob_offset = len_B_verts

            # Add non-stitch vertices to self.vertices
            v_3D = list(panel.rot_trans_panel(panel.panel_vertices))
            v_3D_non_stitch = v_3D[n_stitches_panel:]
            self.vertices += v_3D_non_stitch

            # Assign edge labels to vertices
            for edge in panel.edges:
                if edge.label and edge.stitch_ref is None:
                    # Use vertex range to assign edge labels to non-stitching vertices 
                    e_verts = np.array(edge.vertex_range[1:-1])  # Exclude ends which are located elsewhere and may be in a stitch
                    labeled_verts = e_verts + len_B_verts - n_stitches_panel
                    self.vertex_labels.setdefault(edge.label, []).extend(labeled_verts.tolist())

            #Order face vertices so that face norms are equal to the panel.panel_norm
            self._order_face_vertices(panel, v_3D)

            texture_offset = len(self.vertex_texture)

            for face in panel.panel_faces:
                loc_stitch_ids = [loc_id for loc_id in face if loc_id < n_stitches_panel]

                f_glob_ids = self._get_glob_ids(panel, face)

                if f_glob_ids[0] == f_glob_ids[1] or f_glob_ids[1] == f_glob_ids[2] or f_glob_ids[0] == f_glob_ids[2]:
                    continue #Do not add faces which are points or lines after stitching

                if loc_stitch_ids:
                    self._store_to_orig_lens(panel, face, f_glob_ids, stitch_edges_gt)

                # Add face to self.faces
                self.faces.append(f_glob_ids)

                #Add texture
                tex_id0, tex_id1, tex_id2 = face + texture_offset
                id0, id1, id2 = f_glob_ids
                textured_face = [id0, tex_id0, id1, tex_id1, id2, tex_id2]
                self.faces_with_texture.append(textured_face)

            self.vertex_texture += self.get_v_texture(panel.panel_vertices)

            #Add panel name to stitch_segmentation
            n_non_stitches_panel = len(panel.panel_vertices) - n_stitches_panel
            self.stitch_segmentation += [panel.panel_name] * n_non_stitches_panel

        # NOTE: self.vertices now contains all mesh vertices
        # self.faces now contains all mesh faces

    # !SECTION
    # SECTION -- Serialization routines
    def eval_vertex_normals(self):
        vertex_normals = np.zeros((len(self.vertices), 4))
        for panelname in self.panelNames:
            panel = self.panels[panelname]
            n_stitches_panel = panel.n_stitches

            for face in panel.panel_faces:
                f_glob_ids = self._get_glob_ids(panel, face)
                loc_stitch_ids = [loc_id for loc_id in face if loc_id < n_stitches_panel]
                if loc_stitch_ids:
                    v0, v1, v2 = np.array(self.vertices)[f_glob_ids]
                    face_norm = list(self.calc_norm(v0, v1, v2))
                else:
                    face_norm = panel.norm

                temp_update = face_norm + [1]
                vertex_normals[f_glob_ids] += temp_update

        vertex_normals = vertex_normals[:, :3] / (vertex_normals[:, 3][:, np.newaxis])
        return vertex_normals

    def save_vertex_labels(self):
        """Save labeled vertices"""

        # Add labels on stitched vertices using stitch_id_label
        for v_id, seg_labels in enumerate(self.stitch_segmentation):
            if 'stitch' not in seg_labels[0]:  # Processed all stitches
                break
            for stitch in seg_labels:
                id = int(stitch.split('_')[-1])
                label = self.stitches[id].label
                if label is not None:   # Found a labeled vertex!
                    self.vertex_labels.setdefault(label, []).append(v_id)

        # Save to yaml
        with open(self.paths.g_vert_labels, 'w') as file:
            yaml.dump(self.vertex_labels, file, default_flow_style=False, sort_keys=False)
        
    def save_box_mesh_obj(self, with_normals=False, in_uv_config={}, mat_name='panels_texture'):
        """
        This function creates an obj file of the generated box mesh from pattern and stores it to save_path.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * save_path (str): The path where the obj file is stored
            * filename (str): Name of the boxmmesh
        """
        if not self.loaded:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Pattern is not yet loaded. Nothing saved')
            return
        
        uv_config = {  # Defaults
            'seam_width': 0.5,
            'dpi': 600,
            'fabric_grain_texture_path': None,  
            'fabric_grain_resolution': 1,
        }
        # Update with incoming values, if any
        uv_config.update(in_uv_config)

        uvs = texture_mesh_islands(
            texture_coords=np.array(self.vertex_texture),
            face_texture_coords=np.array([[tex_id0, tex_id1, tex_id2] for _, tex_id0, _, tex_id1, _, tex_id2, in self.faces_with_texture]), 
            out_texture_image_path=self.paths.g_texture,
            out_fabric_tex_image_path=self.paths.g_texture_fabric,
            out_mtl_file_path=self.paths.g_mtl,
            boundary_width=uv_config['seam_width'], 
            dpi=uv_config['dpi'], 
            background_img_path=uv_config['fabric_grain_texture_path'],
            background_resolution=uv_config['fabric_grain_resolution'],
            mat_name=mat_name
        )
        save_obj(
            self.paths.g_box_mesh, 
            self.vertices, 
            self.faces_with_texture, 
            uvs, 
            vert_normals=self.eval_vertex_normals() if with_normals else None,
            mtl_file_name=self.paths.g_mtl.name,
            mat_name=mat_name
        )
            
    def save_segmentation(self):
        """
        This function stores the self.stitch_segmentation list as a txt file to save_path.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * save_path (str): The path where the txt file is stored
            * filename (str): Name of the stitch segmentation file
        """
        if not self.loaded:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Pattern is not yet loaded. Nothing saved')
            return

        rows = self.stitch_segmentation
        with open(self.paths.g_mesh_segmentation, 'w') as file:
            for row in rows:
                # Join the entries in the row with a delimiter (e.g., comma)
                if isinstance(row,list):
                    row_data = ','.join(row)
                else:
                    row_data = row

                # Write the row to the file
                file.write(row_data + '\n')

    def save_orig_lens(self,):
        """
        This function stores the self.orig_lens dict as a pickle file to save_path.
        Self.orig_lens is a dict indexed by two global vertex indices and contains the ground truth length
        between those vertices in their 2D setting.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * save_path (str): The path where the pickle file is stored
            * filename (str): Name of the orig_lens file
        """
        if not self.loaded:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Pattern is not yet loaded. Nothing saved')
            return

        with open(self.paths.g_orig_edge_len, 'wb') as file:
            pickle.dump(self.orig_lens, file)

    def serialize(self, paths: PathCofig, tag='', 
                  with_3d=False, with_text=False, view_ids=False, 
                  empty_ok=False,
                  with_v_norms=False, 
                  store_panels=False,
                  uv_config={}
        ):
        """
        This function stores (annotated) visualisations (png,svg) of the pattern, the box mesh as an .obj file,
        the segmentation as a .txt file and the ground truth lengths dict as a .pickle file by overloading
        the serialize function of core.VisPattern.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * path (str): The path where the files get stored
            * to_subfolder (bool): if True, files will be stored in a subfolder rather than directly to path
            * with_3d (bool): if True, stores the pattern in 3d
            * annotated (bool): if True, stores visualisations without annotations
            * not_annotated (bool): if True, stores visualisations with annotations
        """
        if not self.loaded:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Pattern is not yet loaded. Nothing saved')
            return

        self.paths = paths    
        log_dir = super().serialize(self.paths.out_el, to_subfolder=False, tag=tag, with_3d=with_3d,
                                    with_text=with_text, view_ids=view_ids, empty_ok=empty_ok)

        if store_panels:
            # Store panel
            for panel in self.panels.values():
                folder_path = Path(log_dir) / "panels"
                panel.save_panel_mesh_obj(folder_path)
            print(f"Stored panels to {folder_path}...")


        self.save_box_mesh_obj(with_normals=with_v_norms, in_uv_config=uv_config)
        self.save_segmentation()
        self.save_orig_lens()
        self.save_vertex_labels()

        # Copy yaml files
        if self.paths.in_design_params.exists():
            shutil.copy(self.paths.in_design_params, self.paths.design_params)
        else:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Path does not exist: {self.paths.in_design_params}')
        if self.paths.in_body_mes.exists():
            shutil.copy(self.paths.in_body_mes, self.paths.body_mes)
        else:
            print(f'{self.__class__.__name__}::{self.name}::WARNING::Path does not exist: {self.paths.in_body_mes}')

        return log_dir
    # !SECTION