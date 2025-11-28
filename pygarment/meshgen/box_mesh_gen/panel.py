"""Panel representation for box mesh generation."""

from pathlib import Path
from typing import List, Tuple

import igl
import numpy as np
import matplotlib.pyplot as plt

import pygarment.meshgen.triangulation_utils as tri_utils
from pygarment.pattern import rotation as rotation_tools
from pygarment.pattern.core import BasicPattern
from pygarment.meshgen.pattern_spec import PanelSpec
from pygarment.meshgen.box_mesh_gen.errors import PatternLoadingError, NormError
from pygarment.meshgen.box_mesh_gen.edge import Edge


class Panel:
    """
    Represents a panel of the pattern.

    Parameters
    ----------
    panel_spec : PanelSpec
        Panel specification containing translation, rotation, vertices, and edges
    panel_name : str
        Name of the panel
    mesh_resolution : float
        Mesh resolution for vertex spacing along edges
    """

    def __init__(
        self,
        panel_spec: PanelSpec,
        panel_name: str,
        mesh_resolution: float,
    ) -> None:
        self.panel_name = panel_name
        self.translation = panel_spec.translation
        self.rotation = panel_spec.rotation
        self.corner_vertices = np.asarray(panel_spec.vertices)
        self.panel_vertices: list[np.ndarray] = []
        self.panel_faces: list[list[int]] = []
        self.edges: List[Edge] = []
        self.n_stitches = 0  # needed later to decide whether vertex is stitch vertex or not
        self.glob_offset = -1

        for edge_spec in panel_spec.edges:
            edge_obj = Edge(edge_spec, self.corner_vertices, mesh_resolution)
            self.edges.append(edge_obj)

        self.norm: list[float] = []

    def _verts(self, lin_edges: list) -> list:
        """
        Take a sequence of linear edges and process them to extract unique vertices.

        Parameters
        ----------
        lin_edges : list
            Sequence of edges defined by their start and end vertices

        Returns
        -------
        list
            List of unique vertices extracted from lin_edges, arranged in the order they were encountered
        """
        verts = [lin_edges[0][0]]
        for e in lin_edges:
            if not np.array_equal(e[0], verts[-1]):  # avoid adding the vertices of chained edges twice
                verts.append(e[0])
            verts.append(e[1])
        if np.array_equal(verts[0], verts[-1]):  # don't double count the loop origin
            verts.pop(-1)
        return verts

    def _bbox(self, verts_2d: list) -> Tuple[np.ndarray, np.ndarray]:
        """
        Evaluate the 2D bounding box of the current panel and return the panel vertices which are
        located on the bounding box (b_points) as well as the mean point of b_points in 3D.

        Parameters
        ----------
        verts_2d : list
            List of 2D panel edge vertices ordered in a loop

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Tuple containing:
            - b_points_mean_3d: 3D vertex representing the rotated and translated mean point of b_points
            - b_points_3d: Ndarray of 3D vertices representing the rotated and translated b_points
        """
        verts_2d_arr = np.array(verts_2d)
        mi = verts_2d_arr.min(axis=0)
        ma = verts_2d_arr.max(axis=0)
        xs = [mi[0], ma[0]]
        ys = [mi[1], ma[1]]
        # return points on bounding box
        b_points = []
        for v in verts_2d_arr:
            if v[0] in xs or v[1] in ys:
                b_points.append(v)
        if len(b_points) == 2:
            if not any(np.array_equal(arr, mi) for arr in b_points):
                b_points = [b_points[0], mi, b_points[1]]
            else:
                p = [mi[0], ma[1]]
                b_points = [b_points[0], p, b_points[1]]
        elif len(b_points) < 2:
            raise PatternLoadingError("Less than two vertices defining bounding box")

        b_points_3d = self.rot_trans_panel(b_points)
        b_points_mean_2d = np.mean((b_points), axis=0)
        b_points_mean_3d = self.rot_trans_vertex(b_points_mean_2d)

        return b_points_mean_3d, b_points_3d

    def plot(self, pts: list, title: str) -> None:
        """
        Create a scatter plot of points (used for debugging).

        Parameters
        ----------
        pts : list
            Points to be plotted
        title : str
            Title of the scatter plot
        """
        pts_arr = np.array(pts)
        x_values = pts_arr.T[0]
        y_values = pts_arr.T[1]
        plt.scatter(x_values, y_values, c="blue", marker="o", label="Data Points")

        # Annotate the data points with text
        for i in range(len(x_values)):
            plt.annotate(
                f"{i}",
                (x_values[i], y_values[i]),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
            )

        # Customize the plot (optional)
        plt.title(title)
        plt.xlabel("X-axis")
        plt.ylabel("Y-axis")
        plt.legend()
        # plt.axis('square')

        # Show the plot
        plt.show()

    def set_panel_norm(self) -> None:
        """
        Compute the normal direction of the current panel.
        """
        # Take linear version of the edges
        # To correctly process edges with extreme curvatures
        lin_edges = []
        for e in self.edges:
            lin_edges += list(e.linearize(self.panel_vertices))

        verts = self._verts(lin_edges)

        center_3d, verts_3d = self._bbox(verts)

        norms = []
        num_verts_3d = len(verts_3d)
        for i in range(num_verts_3d):
            vert_0 = verts_3d[i]
            vert_1 = verts_3d[(i + 1) % num_verts_3d]
            # Pylance + NP error for unreachanble code -- see https://github.com/numpy/numpy/issues/22146
            # Works ok for numpy 1.23.4+
            norm = np.cross(vert_0 - center_3d, vert_1 - center_3d)
            norm /= np.linalg.norm(norm)
            norms.append(norm)

        # Current norm direction
        avg_norm = sum(norms) / len(norms)
        if np.linalg.norm(avg_norm) == 0 or np.any(np.isnan(avg_norm)):
            raise NormError(
                f"{self.__class__.__name__}::ERROR::invalid panel norm for {self.panel_name}; "
                f"norms: {norms}; avg_norm: {avg_norm}"
            )
        else:
            final_norm = list(avg_norm / np.linalg.norm(avg_norm))

        # solve float errors
        for i, ni in enumerate(final_norm):
            if np.isclose([ni], [0.0]):
                final_norm[i] = 0.0

        self.norm = final_norm

    def rot_trans_vertex(self, vertex: np.ndarray) -> np.ndarray:
        """
        Transform a 2D vertex into a 3D vertex by rotating it with
        respect to the XYZ Euler angles and applying the specified translation.

        Parameters
        ----------
        vertex : np.ndarray
            Coordinates of the 2D vertex to be transformed

        Returns
        -------
        np.ndarray
            Coordinates of the rotated and translated 3D vertex
        """
        rot_matrix = rotation_tools.euler_xyz_to_R(self.rotation)
        r_t_vertex = BasicPattern._point_in_3D(vertex, rot_matrix, self.translation)
        return r_t_vertex

    def rot_trans_panel(self, vertices: list) -> np.ndarray:
        """
        Transform multiple 2D vertices into 3D vertices by rotating them with
        respect to the XYZ Euler angles and applying the specified translation.

        Parameters
        ----------
        vertices : list
            Coordinates of the 2D vertices to be transformed

        Returns
        -------
        np.ndarray
            Coordinates of the rotated and translated 3D vertices
        """
        if len(vertices) == 0:
            return np.array([])
        rot_matrix = rotation_tools.euler_xyz_to_R(self.rotation)
        r_t_vertices = np.vstack(
            tuple(
                [
                    BasicPattern._point_in_3D(v, rot_matrix, self.translation)
                    for v in np.array(vertices)
                ]
            )
        )
        return r_t_vertices

    def _get_exist_idx(self, find_list: np.ndarray) -> int:
        """
        Return the index of find_list (start or end vertex) in panel.panel_vertices.
        If find_list is not in panel.panel_vertices, find_list is first added to panel.panel_vertices.

        Parameters
        ----------
        find_list : np.ndarray
            Either start or end vertex of an edge

        Returns
        -------
        int
            Index of find_list (start or end vertex) in panel.panel_vertices
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
            else:  # n_found_indices > 1
                raise PatternLoadingError(
                    f"{self.__class__.__name__}::{self.panel_name}::Corner stitch vertex "
                    f"has been added more than once to panel vertices!"
                )

    def store_edge_verts(self, edge: Edge, edge_in_vertices: list) -> None:
        """
        Store the panel.panel_vertices indices of the "start" vertex,
        "edge_in_vertices" vertices, and "end" vertex of edge into edge.vertex_range.

        Parameters
        ----------
        edge : Edge
            Edge object whose vertex indices are stored
        edge_in_vertices : list
            Equally spread vertices along edge (without start and end vertex)
        """
        start, end = edge.endpoints
        start_index = self._get_exist_idx(start)

        begin_in = len(self.panel_vertices)
        end_in = begin_in + len(edge_in_vertices)  # exclusive

        for v in edge_in_vertices:
            self.panel_vertices.append(v)

        end_index = self._get_exist_idx(end)

        edge.set_vertex_range(start_index, begin_in, end_in, end_index)

    def sort_edges_by_stitchid(self) -> Tuple[int, list]:
        """
        Sort the panel's edges by their edge_id (stitch edges first) and
        return them as well as the number of edges that are part of a stitch.

        Returns
        -------
        Tuple[int, list]
            Tuple containing:
            - n_stitch_edges: number of panel edges that are part of a stitch
            - sorted_edges: list containing the stitch_edges first and then the non-stitch edges
        """
        edges = self.edges
        stitch_edges = []
        non_stitch_edges = []
        for edge_id, edge in enumerate(edges):
            if edge.stitch_ref is not None:
                stitch_edges.append((edge_id, edge))
            else:
                non_stitch_edges.append((edge_id, edge))
        n_stitch_edges = len(stitch_edges)
        sorted_edges = stitch_edges + non_stitch_edges
        return n_stitch_edges, sorted_edges

    def gen_panel_mesh(self, mesh_resolution: float, plot: bool = False, check: bool = False) -> None:
        """
        Generate the vertices inside the panel using the vertices along the edges.

        Parameters
        ----------
        mesh_resolution : float
            Mesh resolution for triangulation
        plot : bool
            Indicates if triangle mesh should be plotted
        check : bool
            Indicates if point coordinates should be compared
        """
        points = self.panel_vertices
        len_points = len(points)
        edge_verts_ids = tri_utils.get_edge_vert_ids(self.edges)

        cdt_mesh = tri_utils.Mesh_2_Constrained_Delaunay_triangulation_2()
        cdt_points_mesh = tri_utils.create_cdt_points(cdt_mesh, points)
        tri_utils.cdt_insert_constraints(cdt_mesh, cdt_points_mesh, edge_verts_ids)

        # Meshing the triangulation with default shape criterion; i.e. sqrt(1/(4 * 0.125)) = sqrt(2)
        tri_utils.CGAL_Mesh_2.refine_Delaunay_mesh_2(
            cdt_mesh, tri_utils.Delaunay_mesh_size_criteria_2(0.125, 1.43 * mesh_resolution)
        )  # 1.475

        if plot:
            # Mark faces that are inside the domain
            face_info = tri_utils.mark_domain(cdt_mesh)
            tri_utils.plot_triangulation(cdt_mesh, face_info)

        keep_pts_f = tri_utils.get_keep_vertices(cdt_mesh, len_points)

        # Triangulate mesh without newly inserted boundary points
        cdt = tri_utils.Constrained_Delaunay_triangulation_2()
        cdt_points = tri_utils.create_cdt_points(cdt, keep_pts_f)
        new_points = tri_utils.cdt_insert_constraints(cdt, cdt_points, edge_verts_ids)

        # Faces without accidentally inserted points -- again!
        # NOTE: point insertion might be a sign of degenerate triangles.
        # But instead a separate check was added
        f = list(tri_utils.get_face_v_ids(cdt, keep_pts_f, new_points, check=check, plot=plot))

        # Store
        self.panel_vertices = keep_pts_f
        self.panel_faces = f

    def is_manifold(self, tol: float = 1e-2) -> bool:
        """
        Check if the panel mesh is manifold.

        Parameters
        ----------
        tol : float
            Tolerance for manifold check

        Returns
        -------
        bool
            True if manifold, False otherwise
        """
        return tri_utils.is_manifold(
            np.asarray(self.panel_faces),
            np.asarray(self.panel_vertices),
            tol=tol,
        )

    def save_panel_mesh_obj(self, folder_path: Path) -> None:
        """
        Create an obj file of the generated panel mesh and store it to folder_path.
        Assumes that panel meshes have already been generated.

        Parameters
        ----------
        folder_path : Path
            Path to folder where obj file will be saved
        """
        folder_path.mkdir(exist_ok=True, parents=True)
        filepath = folder_path / (self.panel_name + ".obj")

        v = self.rot_trans_panel(self.panel_vertices)
        f = np.array(self.panel_faces)

        igl.write_triangle_mesh(str(filepath), v, f)

