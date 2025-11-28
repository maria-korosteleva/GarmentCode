"""Box mesh generation from pattern specifications."""

import pickle
import shutil
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import svgpathtools as svgpath
import yaml

import pygarment.pattern.wrappers as wrappers
import pygarment.pattern.utils as pat_utils
from config import PathCofig
from pygarment.meshgen.render.texture_utils import texture_mesh_islands, save_obj
from pygarment.meshgen.pattern_spec import PatternSpec, StitchSpec
from pygarment.meshgen.box_mesh_gen.errors import (
    PatternLoadingError,
    MultiStitchingError,
    StitchingError,
    DegenerateTrianglesError,
)
from pygarment.meshgen.box_mesh_gen.panel import Panel
from pygarment.meshgen.box_mesh_gen.edge import Edge
from pygarment.meshgen.box_mesh_gen.seam import Seam
from pygarment.meshgen.box_mesh_gen.stitch_types import (
    StitchIdentifier,
    PanelIdentifier,
    SegmentationEntry,
    EdgeLabel
)
from loguru import logger


class BoxMesh(wrappers.VisPattern):
    """
    Extends a pattern specification in custom JSON format to generate a box mesh from the pattern.

    Parameters
    ----------
    path : str | Path
        Path to pattern template in custom JSON format
    res : float
        Mesh resolution (vertices are spread with distance ~res cm). Default: 1.0
    """

    crotch_vertex_id: Optional[int] = None

    def __init__(self, path: str | Path, res: float = 1.0) -> None:
        super(BoxMesh, self).__init__(path)
        self.mesh_resolution = res  # Vertices are spread with distance ~mesh_resolution cm
        self.loaded = False

        # Convert pattern dict to PatternSpec
        self.pattern_spec = PatternSpec.from_dict(self.pattern)

        self.panels: dict[str, Panel] = {}
        self.stitches: list[Seam] = []
        self.vertices: list[np.ndarray] = []
        self.faces: list[list[int]] = []
        self.orig_lens: dict[tuple[int, int], float] = {}

        self.verts_loc_glob: dict[tuple[str, int], int] = {}
        self.verts_glob_loc: list[list[tuple[str, int]]] = []
        self.stitch_segmentation: list[list[SegmentationEntry]] = []
        self.vertex_normals: list[np.ndarray] = []
        self.faces_with_texture: list[list[int]] = []
        self.vertex_texture: list[list[float]] = []
        self.vertex_labels: dict[str, list[int]] = {}  # Additional vertex labels coming from panel edges' labels

    @property
    def panel_names(self) -> list[str]:
        """
        Get the ordered list of panel names.

        This property delegates to the parent class's `panel_order()` method,
        which returns a cached list of panel names ordered by their 3D translation
        (X -> Y -> Z).

        Returns
        -------
        list[str]
            Ordered list of panel names
        """
        return self.panel_order()

    def load(self) -> None:
        """
        Load all relevant functions and print their time consumptions.
        """
        if self.is_self_intersecting():
            logger.warning("Provided pattern has self-intersecting panels. Simulation might crash")

        self.load_panels()
        self.gen_panel_meshes()

        # NOTE: Collapse stitch vertices and store to self.vertices as well as their stitch_id to self.stitch_segmentation
        self.collapse_stitch_vertices()

        self.finalise_mesh()
        self.loaded = True

    def load_panels(self) -> None:
        """
        For each panel of the pattern create a panel object and load stitching info + set number of
        stitching edge vertices.
        """
        for panel_name in self.panel_names:
            panel_spec = self.pattern_spec.panels[panel_name]
            panel = Panel(panel_spec, panel_name, self.mesh_resolution)
            self.panels[panel_name] = panel

        # Load stitching info
        self.read_stitches()

    def _get_stitch_edge_info(
        self, stitch_spec: StitchSpec, side_id: int
    ) -> tuple[str, int, Edge]:
        """
        Get the edge defined by stitch specification and side ID.

        Parameters
        ----------
        stitch_spec : StitchSpec
            Stitch specification
        side_id : int
            Side ID (0 or 1)

        Returns
        -------
        Tuple[str, int, Edge]
            Tuple containing:
            - panel_name: Panel name of the edge
            - edge_id: Edge index in the panel
            - edge: Edge object

        Raises
        ------
        PatternLoadingError
            If the edge cannot be found
        """
        if side_id == 0:
            side_spec = stitch_spec.side_0
        elif side_id == 1:
            side_spec = stitch_spec.side_1
        else:
            raise ValueError(f"Invalid side_id: {side_id}, must be 0 or 1")

        panel_name = side_spec.panel
        edge_id = side_spec.edge
        ret_panel = self.panels[panel_name]
        try:
            edge = ret_panel.edges[edge_id]
        except (IndexError, KeyError) as e:
            logger.error(f"Provided pattern fails for stitch and {[panel_name, edge_id]}")
            raise PatternLoadingError(
                f"{self.__class__.__name__}::{self.name}::ERROR::Provided pattern"
                f" fails for stitch and {[panel_name, edge_id]}"
            ) from e
        else:
            return panel_name, edge_id, edge

    def read_stitches(self) -> None:
        """
        Load the stitching information from the spec and determine the number of mesh
        vertices to be generated on edges, such that they match in the stitches.
        """
        multi_stitches_check: list[tuple[str, int]] = []
        if self.pattern_spec.stitches:
            for stitch_id, stitch_spec in enumerate(self.pattern_spec.stitches):
                panel_name_0, edge_id0, edge0 = self._get_stitch_edge_info(stitch_spec, 0)
                panel_name_1, edge_id1, edge1 = self._get_stitch_edge_info(stitch_spec, 1)

                stitch = Seam(
                    panel_name_0,
                    edge_id0,
                    panel_name_1,
                    edge_id1,
                    swap=not stitch_spec.right_wrong,
                )
                self.stitches.append(stitch)

                edge0.stitch_ref, edge1.stitch_ref = stitch, stitch

                n_0, n_1 = edge0.n_edge_verts, edge1.n_edge_verts
                # Assign n of longer edge
                if edge0.curve is not None and edge1.curve is not None:
                    n = n_0 if edge0.curve.length() > edge1.curve.length() else n_1
                else:
                    n = max(n_0, n_1)
                edge0.n_edge_verts = n
                edge1.n_edge_verts = n
                stitch.n_verts = n
                # ---
                multi_edge = [
                    (p, e)
                    for (p, e) in [(panel_name_0, edge_id0), (panel_name_1, edge_id1)]
                    if (p, e) in multi_stitches_check
                ]
                if multi_edge:
                    raise MultiStitchingError(
                        f"{self.__class__.__name__}::{self.name}::ERROR::Multi stitching"
                        f" detected at stitch id {stitch_id} from {multi_edge}"
                    )
                else:
                    multi_stitches_check.append((panel_name_0, edge_id0))
                    multi_stitches_check.append((panel_name_1, edge_id1))

                # Propagate Edge labeling
                if edge0.label or edge1.label:
                    if edge0.label and edge1.label and edge0.label != edge1.label:  # Sanity check
                        raise ValueError(
                            f"{self.__class__.__name__}::{self.name}::ERROR::Edge labels "
                            f"in stitch do not match: {edge0.label} and {edge1.label}"
                        )
                    stitch.label = edge0.label if edge0.label else edge1.label
        else:
            logger.info("No stitching information provided")

    def _get_edge_in_verts(self, edge: Edge, plot: bool = False) -> list:
        """
        Generate the pre-defined number of vertices for each edge.

        Parameters
        ----------
        edge : Edge
            Edge object for which the vertices are generated
        plot : bool
            If True, plots edge vertices

        Returns
        -------
        list
            n_edge_verts equally spread vertices along edge
        """
        n = edge.n_edge_verts

        edge_in_vertices = []
        t_vals: list[float] = np.linspace(0, 1, n).tolist()

        if isinstance(edge.curve, svgpath.QuadraticBezier) or isinstance(edge.curve, svgpath.CubicBezier):
            # to achieve equal spread along bezier curve
            curve_lengths = np.linspace(0, 1, n) * edge.curve.length()
            t_vals = [edge.curve.ilength(c_len) for c_len in curve_lengths]

        ts = t_vals[1 : (n - 1)]  # remove start and end from "inside vertices"
        if isinstance(edge.curve, svgpath.Arc):
            for t in ts:
                p = pat_utils.c_to_np(edge.curve.point(t))
                edge_in_vertices.append(p)
        elif edge.curve is not None:
            points = edge.curve.points(ts)  # faster than .point(t) but unavailable for Arc
            edge_in_vertices = [pat_utils.c_to_np(p) for p in points]
        else:
            raise ValueError(f"Edge {edge.label} has no curve")

        if plot:
            c_type = "circle"
            if isinstance(edge.curve, svgpath.QuadraticBezier) or isinstance(edge.curve, svgpath.CubicBezier):
                c_type = "bezier"
            elif isinstance(edge.curve, svgpath.Line):
                c_type = "linear"

            show_verts = np.array([edge.endpoints[0]] + list(edge_in_vertices) + [edge.endpoints[1]])

            lis = show_verts.T
            x, y = lis
            x = list(x)
            y = list(y)
            plt.scatter(x, y)

            plt.axis("square")
            plt.title(c_type)

            for i in range(len(show_verts)):
                plt.annotate(str(i), (x[i], y[i]), textcoords="offset points", xytext=(0, 10), ha="center")

            plt.show()

        return edge_in_vertices

    def gen_panel_meshes(self) -> None:
        """
        For each Panel:
            * For each edge generate its edge vertices and store them in panel.panel_vertices.
              Further, store "start", "inside-edge", and "end" indices for each edge vertex in edge.vertex_range
            * Generate vertices inside the panel and its triangles using CGAL and store them in panel.panel_vertices
              and panel.panel_triangles, respectively.
        """
        for panelname in self.panel_names:
            panel = self.panels[panelname]

            # Sort panel.edges by stitch id
            n_stitch_edges, sorted_edges = panel.sort_edges_by_stitchid()

            for i, (_, edge) in enumerate(sorted_edges):
                # Get vertices for edge (without start, end)
                edge_in_vertices = self._get_edge_in_verts(edge, plot=False)

                # Store start, inside, and end vertices to Panel.panel_vertices and indices to edge.vertex_range
                panel.store_edge_verts(edge, edge_in_vertices)

                if i == n_stitch_edges - 1:
                    panel.n_stitches = len(
                        panel.panel_vertices
                    )  # until now we only have stitch vertices in Panel.panel_vertices

            # Set panel norm
            panel.set_panel_norm()
            # Generate panel mesh and store them in panel.panel_vertices and panel.panel_faces
            panel.gen_panel_mesh(self.mesh_resolution)

            # Sanity check
            if not panel.is_manifold():
                raise DegenerateTrianglesError(
                    f"{self.__class__.__name__}::ERROR::{self.name}::{panel.panel_name}:"
                    ":panel contains degenerate triangles"
                )

    def _swap_stitch_ranges(self, stitch: Seam) -> tuple[list, list]:
        """
        Return the stitch_ranges of stitched edges in the correct order,
        so that the correct edge vertices are stitched together.

        Parameters
        ----------
        stitch : Seam
            Desired stitch to be updated

        Returns
        -------
        tuple[list, list]
            Tuple containing:
            - stitch_range_1: Correctly ordered indices for stitch.edge_1 in stitch.panel_1
            - stitch_range_2: Correctly ordered indices into stitch.edge_2 in stitch.panel_2
        """
        panel1, panel2 = self.panels[stitch.panel_1], self.panels[stitch.panel_2]

        stitch_range_1 = panel1.edges[stitch.edge_1].vertex_range
        stitch_range_2 = panel2.edges[stitch.edge_2].vertex_range

        # Force existing swap
        if stitch.swap:
            stitch_range_1 = stitch_range_1[::-1]

        return stitch_range_1, stitch_range_2

    def _stitch_same_loc_vertex(self, panel1: Panel, loc_id1: int, glob_idx: int, stitch_id: int) -> None:
        """
        Stitch two vertices together which are exactly the same local vertex and
        have not participated in a stitch so far.

        Parameters
        ----------
        panel1 : Panel
            Panel object participating in stitch
        loc_id1 : int
            Local identifier of a vertex into panel1.panel_vertices that is stitched together with itself
        glob_idx : int
            Global index of vertex that is stitched together with itself
        stitch_id : int
            Stitch identifier indicating which stitch is currently performed
        """
        p1_name = panel1.panel_name
        self.verts_loc_glob[(p1_name, loc_id1)] = glob_idx
        self.verts_glob_loc.append([(p1_name, loc_id1)])
        v_2D = panel1.panel_vertices[loc_id1]
        self.vertices.append(panel1.rot_trans_vertex(v_2D))
        self.stitch_segmentation.append([StitchIdentifier(stitch_id=stitch_id)])

    def _stitch_two_diff_existent_glob_verts(
        self, glob1: int, glob2: int, glob_idx: int, stitch_id: int
    ) -> None:
        """
        Stitch two vertices together where both have already participated in a stitch.

        Parameters
        ----------
        glob1 : int
            Global identifier of first stitch vertex into self.vertices
        glob2 : int
            Global identifier of second stitch vertex into self.vertices
        glob_idx : int
            Current number of vertices stored in self.vertices
        stitch_id : int
            Stitch identifier indicating which stitch is currently performed
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
        # Extend the list at glob_min with stitch IDs from glob_max and add new stitch_id
        self.stitch_segmentation[glob_min].extend(copy_stitch_ids)
        self.stitch_segmentation[glob_min].append(StitchIdentifier(stitch_id=stitch_id))
        del self.stitch_segmentation[glob_max]

    def _stitch_one_existent_glob_vert(
        self,
        panel_glob: Panel,
        panel_not_glob: Panel,
        loc_id_glob: int,
        loc_id_not_glob: int,
        stitch_id: int,
    ) -> None:
        """
        Stitch two vertices together where only one of them has already participated in a stitch.

        Parameters
        ----------
        panel_glob : Panel
            Panel object referenced by vertex that has already participated in a stitch
        panel_not_glob : Panel
            Panel object referenced by vertex that has not yet participated in a stitch
        loc_id_glob : int
            Local identifier of a stitch vertex into panel_glob.panel_vertices.
            This vertex has already participated in a stitch.
        loc_id_not_glob : int
            Local identifier of a stitch vertex into panel_not_glob.panel_vertices.
            This vertex has not participated in a stitch so far.
        stitch_id : int
            Stitch identifier indicating which stitch is currently performed
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
        self.stitch_segmentation[glob].append(StitchIdentifier(stitch_id=stitch_id))

    def _stitch_none_existent_glob_verts(
        self, panel1: Panel, panel2: Panel, loc_id1: int, loc_id2: int, glob_idx: int, stitch_id: int
    ) -> None:
        """
        Stitch two vertices together where both of them have not yet participated in a stitch.

        Parameters
        ----------
        panel1 : Panel
            Panel object referenced by the first stitch vertex
        panel2 : Panel
            Panel object referenced by the second stitch vertex
        loc_id1 : int
            Local identifier of the first stitch vertex into panel1.panel_vertices
        loc_id2 : int
            Local identifier of the second stitch vertex into panel2.panel_vertices
        glob_idx : int
            Current number of vertices stored in self.vertices
        stitch_id : int
            Stitch identifier indicating which stitch is currently performed
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
        self.stitch_segmentation.append([StitchIdentifier(stitch_id=stitch_id)])

    def _stitch_vertices(self) -> dict[tuple[str, int], list]:
        """
        Determine if the stitch_range of one edge has to be reversed,
        compute stitch vertices by taking the mean of corresponding 3D panel vertex pairs,
        and store relationships.

        Returns
        -------
        dict[tuple[str, int], list]
            Dictionary storing the local vertex indices to which a local vertex
            of the same panel is stitched together
        """
        # Collapse stitch vertices
        same_panel_stitching_dict: dict[tuple[str, int], list] = {}  # Store stichings of same panel
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
                if stitch.panel_1 == stitch.panel_2 and loc_id1 == loc_id2:  # same vertex
                    if (stitch.panel_1, loc_id1) not in self.verts_loc_glob.keys():
                        self._stitch_same_loc_vertex(panel1, loc_id1, glob_idx, stitch_id)
                        glob_idx += 1
                    else:
                        glob_id = self.verts_loc_glob[(stitch.panel_1, loc_id1)]
                        self.stitch_segmentation[glob_id].append(StitchIdentifier(stitch_id=stitch_id))
                else:
                    v1_glob_exists = (stitch.panel_1, loc_id1) in self.verts_loc_glob.keys()
                    v2_glob_exists = (stitch.panel_2, loc_id2) in self.verts_loc_glob.keys()
                    if v1_glob_exists and v2_glob_exists:  # both exist
                        glob1 = self.verts_loc_glob[(stitch.panel_1, loc_id1)]
                        glob2 = self.verts_loc_glob[(stitch.panel_2, loc_id2)]
                        if glob1 != glob2:
                            self._stitch_two_diff_existent_glob_verts(glob1, glob2, glob_idx, stitch_id)
                            glob_idx -= 1
                    elif v1_glob_exists:
                        self._stitch_one_existent_glob_vert(panel1, panel2, loc_id1, loc_id2, stitch_id)
                    elif v2_glob_exists:
                        self._stitch_one_existent_glob_vert(panel2, panel1, loc_id2, loc_id1, stitch_id)
                    else:  # none exist
                        self._stitch_none_existent_glob_verts(panel1, panel2, loc_id1, loc_id2, glob_idx, stitch_id)
                        glob_idx += 1

        return same_panel_stitching_dict

    def check_local_vertices_stitching(
        self, dic: dict[tuple[str, int], list], panel_name: str, loc_ids: list[int]
    ) -> bool:
        """
        Check for valid "same panel stitching" based on vertices given as a set of
        local vertex ids and a dictionary with "same panel stitching" information.

        Parameters
        ----------
        dic : dict[tuple[str, int], list]
            Same_panel_stitching_dict, dictionary storing the local vertex indices to which a
            local vertex of the same panel is stitched together
        loc_ids : list[int]
            List of vertex ids representing vertices that are stitched into one global vertex
            in the same panel and are needed to be checked for validity.
        panel_name : str
            Panel name used to identify the panel.

        Returns
        -------
        bool
            True if any local vertex (defined by loc_ids) is stitched together with at least one other
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

    def _group_same_panel_stiches(
        self, inner_list: list[tuple[str, int]]
    ) -> list[tuple[str, list[int]]]:
        """
        Group together stitched vertices that belong to the same panel.

        Parameters
        ----------
        inner_list : list[tuple[str, int]]
            List of tuples representing same panel stitching information,
            where each tuple contains the panel name and a vertex id.

        Returns
        -------
        list[tuple[str, list[int]]]
            List of tuples where the first element is the panel name, and the second
            element is a list of vertex IDs that are stitched together with another vertex of that panel.
        """
        result_dict: dict[str, list[int]] = {}

        for name, value in inner_list:
            if name in result_dict:
                result_dict[name].append(value)
            else:
                result_dict[name] = [value]

        # Filter only the panels with more than one value
        final_result = [(name, values) for name, values in result_dict.items() if len(values) > 1]

        return final_result

    def _check_same_panel_stitching(
        self, dic: dict[tuple[str, int], list], global_ids: list[int]
    ) -> bool:
        """
        Check for stitching of local vertices within the same panel based on a given dictionary
        containing "same panel stitching" information and global vertex IDs representing the end vertices of
        two edges that are stitched together.

        Parameters
        ----------
        dic : dict[tuple[str, int], list]
            Same_panel_stitching_dict, dictionary storing the local vertex indices to which a
            local vertex of the same panel is stitched together
        global_ids : list[int]
            Global vertex IDs representing the end vertices of two edges that are stitched together

        Returns
        -------
        bool
            Returns True if stitching is incorrect: there are local vertices associated with
            the provided global IDs that are stitched together within the same panel;
            otherwise, returns False.
        """
        for g_id in global_ids:
            l_old = self.verts_glob_loc[g_id]  # All local verts corresponding to g_id
            # Groups by panels, if there are multiple vertices from the same panel
            grouped_stitches = self._group_same_panel_stiches(l_old)
            if not dic and grouped_stitches:
                return True
            for panel_name, loc_ids in grouped_stitches:
                if self.check_local_vertices_stitching(dic, panel_name, loc_ids):
                    return True

        return False

    def _valid_stitch_front_end(self, stitch: Seam) -> bool:
        """
        Check if any front and end vertices of the two edges taking part in a stitch
        have been stitched together.

        Parameters
        ----------
        stitch : Seam
            Stitch object

        Returns
        -------
        bool
            Returns False if any front and end vertices of the two edges taking part in a stitch
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

    def _valid_stitch_same_panel(
        self, stitch: Seam, same_panel_stitching_dict: dict[tuple[str, int], list]
    ) -> bool:
        """
        Examine whether the front and end vertices of two edges participating in a
        stitching operation have been improperly stitched together with another vertex from the same panel.

        Parameters
        ----------
        stitch : Seam
            Stitch object
        same_panel_stitching_dict : dict[tuple[str, int], list]
            Dictionary storing the local vertex indices to which a
            local vertex of the same panel is stitched together

        Returns
        -------
        bool
            Returns False if any front and end vertices of two edges participating in a
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
            same_panel_stitching_dict, [s1_glob, e1_glob, s2_glob, e2_glob]
        )

    def _is_stitching_valid(
        self, same_panel_stitching_dict: dict[tuple[str, int], list], front_end_only: bool = False
    ) -> tuple[bool, list[int]]:
        """
        Check validity of a current stitching.

        Parameters
        ----------
        same_panel_stitching_dict : dict[tuple[str, int], list]
            Dictionary storing same panel stitching information
        front_end_only : bool
            If True, only check front-end validity

        Returns
        -------
        tuple[bool, list[int]]
            Tuple containing:
            - valid: True if stitching is valid
            - stitch_ids_invalid: List of invalid stitch IDs
        """
        stitch_ids_invalid: list[int] = []
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

    def collapse_stitch_vertices(self) -> None:
        """
        Perform the stitching and check if any anomalies can be detected.
        """
        # NOTE: don't need this
        # Try the stitching -- performs global vertex matching
        same_panel_stitching_dict = self._stitch_vertices()

        # Check stitches validity: edge collapse (start==end)
        # NOTE: Separating checks by error type to reduce number of invalid stitch orientations to process
        # in each case
        valid, _ = self._is_stitching_valid(same_panel_stitching_dict, front_end_only=False)
        if not valid:
            logger.error("Invalid stitching. Unable to fix")
            raise StitchingError()

    def _get_glob_ids(self, panel: Panel, face: list[int]) -> list[int]:
        """
        Return the global indices of the face vertices.

        Parameters
        ----------
        panel : Panel
            Panel object the face is from
        face : list[int]
            Contains the local indices of the face vertices into panel.panel_faces

        Returns
        -------
        list[int]
            Global indices of face vertices into self.vertices
        """
        glob_indices = []
        n_stitches_panel = panel.n_stitches
        for loc_id in face:
            if loc_id < n_stitches_panel:
                glob_indices.append(self.verts_loc_glob[(panel.panel_name, loc_id)])
            else:
                glob_indices.append(loc_id + panel.glob_offset - n_stitches_panel)

        return glob_indices

    def calc_norm(self, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
        """
        Calculate the norm based on the three points a, b, and c.

        Parameters
        ----------
        a : np.ndarray
            First point taking part in norm calculation
        b : np.ndarray
            Second point taking part in norm calculation
        c : np.ndarray
            Third point taking part in norm calculation

        Returns
        -------
        np.ndarray
            norm(a,b,c) with length 1
        """
        # Calculate the vectors AB and AC
        AB = np.array(b - a)
        AC = np.array(c - a)

        # Calculate the cross product of AB and AC
        n = np.cross(AB, AC)
        n_normalized = n / np.linalg.norm(n)

        return n_normalized

    def _check_norm_local(
        self, idx_a: int, idx_b: int, idx_c: int, panel_norm: list[float], v_3D: list
    ) -> bool:
        """
        Check if the norm defined by the three vertices a,b, and c equals panel_norm.

        Parameters
        ----------
        idx_a : int
            Index of the first vertex into v_3D
        idx_b : int
            Index of the second vertex into v_3D
        idx_c : int
            Index of the third vertex into v_3D
        panel_norm : list[float]
            The norm of a panel to which norm(a,b,c) is compared to
        v_3D : list
            The 3D vertices of a panel

        Returns
        -------
        bool
            True if norm(a,b,c) equals panel_norm, else False
        """
        a, b, c = np.array(v_3D)[[idx_a, idx_b, idx_c]]

        n_normalized = self.calc_norm(a, b, c)

        same_norm = np.allclose(n_normalized, panel_norm)
        return same_norm

    def _order_face_vertices(self, panel: Panel, v_3D: list) -> None:
        """
        Order the face vertices of panel.panel_faces so that the face norms equal the panel's norm.

        Parameters
        ----------
        panel : Panel
            Panel object whose norm is used for comparison
        v_3D : list
            The 3D vertices of panel.panel_vertices
        """
        # Check first face:
        idxa, idxb, idxc = panel.panel_faces[0]
        if not self._check_norm_local(idxa, idxb, idxc, panel.norm, v_3D):
            faces_array = np.array(panel.panel_faces)
            # Swap the 2nd and 3rd columns
            faces_array[:, [1, 2]] = faces_array[:, [2, 1]]
            panel.panel_faces = list(faces_array)

    def _set_el_within_range(self, low: float, up: float, tolerance_factor: float = 0.02) -> float:
        """
        Return a value between low and up based on the tolerance_factor.

        Parameters
        ----------
        low : float
            Lower bound (exclusive)
        up : float
            Upper bound (exclusive)
        tolerance_factor : float
            Influences how close the GT edge length is to low

        Returns
        -------
        float
            New GT edge length close to low
        """
        range_distance = up - low
        tol = tolerance_factor * range_distance
        el = low + tol
        return el

    def _get_seam_gt_el(
        self,
        el_i: float,
        el_j: float,
        el_k: float,
        id1: int,
        id2: int,
        stitch_edges_gt: dict[tuple[int, int], list],
    ) -> float:
        """
        Return the ground truth length of edges between two stitch vertices.

        It returns the minimum edge length if the triangle inequality is satisfied.
        Otherwise, it returns the smallest value that maintains the validity of the adjacent triangles
        (if possible).

        Parameters
        ----------
        el_i : float
            Second edge length of stitch edge i
        el_j : float
            Edge length of edge j which is part of the same triangle
        el_k : float
            Edge length of edge k which is part of the same triangle
        id1 : int
            Global vertex id of first edge vertex (vertex is a stitch vertex)
        id2 : int
            Global vertex id of second edge vertex (vertex is a stitch vertex)
        stitch_edges_gt : dict[tuple[int, int], list[float]]
            Dict storing lower bound, upper bound and current edge length of previously
            encountered edge with vertices id1 and id2

        Returns
        -------
        float
            Ground truth edge length
        """
        low_old, up_old, el_i_old = stitch_edges_gt[(id1, id2)]
        min_el = min([el_i, el_i_old])
        low = max(low_old, abs(el_j - el_k))
        up = min(up_old, el_j + el_k)
        if low < min_el and min_el < up:
            el = min_el
        elif low < up and min_el < low:
            el = self._set_el_within_range(low, up)
        else:
            logger.warning(
                f"Impossible to set ground truth edge length of vertices {id1} and {id2}. "
                f"Simulation is going to crash"
            )
            return low
        return el

    def _store_to_orig_lens(
        self,
        panel: Panel,
        face: list[int],
        f_glob_ids: list[int],
        stitch_edges_gt: dict[tuple[int, int], list[float]],
    ) -> None:
        """
        Store the lengths between the local 2D face vertices
        to self.orig_lens in terms of their global indices.

        Parameters
        ----------
        panel : Panel
            Panel object the face is from
        face : list[int]
            Contains the face vertex indices into panel.panel_vertices
        f_glob_ids : list[int]
            The global indices of the face vertices into self.vertices
        stitch_edges_gt : dict[tuple[int, int], list[float]]
            Dictionary storing stitch edge ground truth information
        """
        # Sort f_glob_ids and get the corresponding indices
        sorted_indices = sorted(range(3), key=lambda i: f_glob_ids[i])

        # Sort f_glob_ids and face (local ids) based on the sorted indices
        glob_id1, glob_id2, glob_id3 = np.array(f_glob_ids)[sorted_indices]
        f_loc_id_1, f_loc_id_2, f_loc_id_3 = face[sorted_indices] # type: ignore

        v1 = panel.panel_vertices[f_loc_id_1]
        v2 = panel.panel_vertices[f_loc_id_2]
        v3 = panel.panel_vertices[f_loc_id_3]

        el1 = float(np.linalg.norm(np.array(v2 - v1)))
        el2 = float(np.linalg.norm(np.array(v3 - v2)))
        el3 = float(np.linalg.norm(np.array(v3 - v1)))

        e1_exists = (glob_id1, glob_id2) in stitch_edges_gt.keys()
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
                stitch_edges_gt[glob_id1, glob_id2] = [
                    max(low1_old, abs(el2 - el3)),
                    min(up1_old, el2 + el3),
                    el1,
                ]
            else:
                stitch_edges_gt[glob_id1, glob_id2] = [abs(el2 - el3), el2 + el3, el1]
        if v2_stitch and v3_stitch:
            if low2_old:
                stitch_edges_gt[glob_id2, glob_id3] = [
                    max(low2_old, abs(el1 - el3)),
                    min(up2_old, el1 + el3),
                    el2,
                ]
            else:
                stitch_edges_gt[glob_id2, glob_id3] = [abs(el1 - el3), el1 + el3, el2]
        if v1_stitch and v3_stitch:
            if low3_old:
                stitch_edges_gt[glob_id1, glob_id3] = [
                    max(low3_old, abs(el1 - el2)),
                    min(up3_old, el1 + el2),
                    el3,
                ]
            else:
                stitch_edges_gt[glob_id1, glob_id3] = [abs(el1 - el2), el1 + el2, el3]

    def get_v_texture(self, panel_vertices: list) -> list:
        """
        Return the minimum x and y value of panel_vertices.

        Parameters
        ----------
        panel_vertices : list
            Panel vertices

        Returns
        -------
        list
            Texture coordinates relative to minimum x and y
        """
        p_v_arr = np.array(panel_vertices)
        trans = [min(p_v_arr[:, 0]), min(p_v_arr[:, 1])]
        v_texture = p_v_arr - trans
        return v_texture.tolist()

    def finalise_mesh(self) -> None:
        """
        Finalize box mesh after stitching has finished:
        * Creates self.faces and self.vertices
        * Creates stitch segmentation
        """
        stitch_edges_gt: dict[tuple[int, int], list[float]] = {}
        # Store original length between stitch vertices and their neighbors
        for panelname in self.panel_names:
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
                    e_verts = np.array(
                        edge.vertex_range[1:-1]
                    )  # Exclude ends which are located elsewhere and may be in a stitch
                    labeled_verts = e_verts + len_B_verts - n_stitches_panel
                    self.vertex_labels.setdefault(edge.label, []).extend(labeled_verts.tolist())

            # Order face vertices so that face norms are equal to the panel.panel_norm
            self._order_face_vertices(panel, v_3D)

            texture_offset = len(self.vertex_texture)

            for face in panel.panel_faces:
                loc_stitch_ids = [loc_id for loc_id in face if loc_id < n_stitches_panel]

                f_glob_ids = self._get_glob_ids(panel, face)

                if (
                    f_glob_ids[0] == f_glob_ids[1]
                    or f_glob_ids[1] == f_glob_ids[2]
                    or f_glob_ids[0] == f_glob_ids[2]
                ):
                    continue  # Do not add faces which are points or lines after stitching

                if loc_stitch_ids:
                    self._store_to_orig_lens(panel, face, f_glob_ids, stitch_edges_gt)

                # Add face to self.faces
                self.faces.append(f_glob_ids)

                # Add texture
                tex_id0, tex_id1, tex_id2 = face + texture_offset # type:ignore
                id0, id1, id2 = f_glob_ids
                textured_face = [id0, tex_id0, id1, tex_id1, id2, tex_id2]
                self.faces_with_texture.append(textured_face)

            self.vertex_texture += self.get_v_texture(panel.panel_vertices)

            # Add panel name to stitch_segmentation (as list for consistency)
            n_non_stitches_panel = len(panel.panel_vertices) - n_stitches_panel
            self.stitch_segmentation.extend([[PanelIdentifier(panel_name=panel.panel_name)]] * n_non_stitches_panel)

        # NOTE: self.vertices now contains all mesh vertices
        # self.faces now contains all mesh faces

        self.crotch_vertex_id = self._identify_crotch_vertex()
        logger.debug(f"Crotch vertex global ID: {self.crotch_vertex_id}")

    def _identify_crotch_vertex(self) -> int:
        """
        Identify and return the global vertex ID of the crotch point.

        The crotch point is where the 'crotch' and 'inside' seams meet.
        It is marked by the 'crotch_point_seam' label on an edge.
        The crotch vertex is the end vertex of the edge with this label
        (where it connects to the inside seam).

        Returns
        -------
        int
            Global vertex ID of the crotch vertex, or -1 if not found
        """
        crotch_vertex_global_id = -1

        # Debug: Check what panels we have
        pants_panels = [
            name for name in self.panels.keys() if "pants" in name.lower() or "pant" in name.lower()
        ]
        logger.debug(f"Looking for crotch vertex in panels: {pants_panels}")

        # Find edges with 'crotch_point_seam' label
        found_crotch_edges = []
        for panel_name, panel in self.panels.items():
            if "pants" not in panel_name.lower() and "pant" not in panel_name.lower():
                continue

            # Debug: Check all edge labels in this panel
            edge_labels = [(idx, edge.label) for idx, edge in enumerate(panel.edges) if edge.label]
            if edge_labels:
                logger.debug(f"Panel {panel_name} has labeled edges: {edge_labels}")

            for edge_idx, edge in enumerate(panel.edges):
                if edge.label == EdgeLabel.CROTCH_POINT_SEAM.value:
                    found_crotch_edges.append((panel_name, edge_idx, edge))
                    logger.debug(
                        f'Found edge with "{EdgeLabel.CROTCH_POINT_SEAM.value}" label in panel {panel_name}, edge_idx {edge_idx}'
                    )

        if not found_crotch_edges:
            logger.warning('No edge with "crotch_point_seam" label found in any pants panel')
            return -1

        # Process found crotch edges
        for panel_name, edge_idx, crotch_edge in found_crotch_edges:
            # The crotch vertex is at the end of this edge (where it connects to inside seam)
            if not crotch_edge.vertex_range:
                logger.warning(
                    f'Edge with "crotch_point_seam" label has no vertex_range for panel {panel_name}'
                )
                continue

            # The end vertex is the last one in the vertex_range
            end_local_id = crotch_edge.vertex_range[-1]
            logger.debug(
                f"Looking for vertex (panel={panel_name}, local_id={end_local_id}) in verts_loc_glob"
            )

            end_global_id = self.verts_loc_glob.get((panel_name, end_local_id))

            if end_global_id is None:
                # Debug: Check what vertices are available for this panel
                panel_verts = {
                    k: v for k, v in self.verts_loc_glob.items() if k[0] == panel_name
                }
                logger.debug(
                    f"Vertex not found in verts_loc_glob. Available vertices for {panel_name}: "
                    f"{list(panel_verts.keys())[:10]}... (showing first 10)"
                )
                continue

            crotch_vertex_global_id = int(end_global_id)
            logger.debug(
                f"Found crotch vertex for panel {panel_name}: "
                f"local_id={end_local_id}, global_id={crotch_vertex_global_id}"
            )
            break

        if crotch_vertex_global_id == -1:
            logger.warning("Could not identify crotch vertex - vertex not in verts_loc_glob")
        else:
            # Label all vertices below the crotch vertex (in Y direction)
            crotch_y = self.vertices[crotch_vertex_global_id][1]
            below_crotch_vertices = [i for i, v in enumerate(self.vertices) if v[1] < crotch_y]
            self.vertex_labels.setdefault(EdgeLabel.CROTCH.value, []).extend(below_crotch_vertices)
            logger.debug(f"Labeled {len(below_crotch_vertices)} vertices below crotch (y < {crotch_y:.2f})")

        return crotch_vertex_global_id

    def eval_vertex_normals(self) -> np.ndarray:
        """
        Evaluate vertex normals for the mesh.

        Returns
        -------
        np.ndarray
            Vertex normals array
        """
        vertex_normals = np.zeros((len(self.vertices), 4))
        for panelname in self.panel_names:
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

    def save_vertex_labels(self) -> None:
        """Save labeled vertices to YAML file."""
        # Add labels on stitched vertices using stitch_id_label
        for v_id, seg_labels in enumerate(self.stitch_segmentation):
            # seg_labels is always a list now
            if not seg_labels or not seg_labels[0].is_stitch():  # Processed all stitches
                break
            for entry in seg_labels:
                if isinstance(entry, StitchIdentifier):
                    label = self.stitches[entry.stitch_id].label
                    if label is not None:  # Found a labeled vertex!
                        # Convert label string to EdgeLabel enum if it exists
                        label_str = str(label) if not isinstance(label, EdgeLabel) else label.value
                        self.vertex_labels.setdefault(label_str, []).append(v_id)

        # Save to yaml
        with open(self.paths.g_vert_labels, "w") as file:
            yaml.dump(self.vertex_labels, file, default_flow_style=False, sort_keys=False)

    def save_box_mesh_obj(
        self, with_normals: bool = False, in_uv_config: dict = {}, mat_name: str = "panels_texture"
    ) -> None:
        """
        Create an obj file of the generated box mesh from pattern and store it to save_path.

        Parameters
        ----------
        with_normals : bool
            Whether to include vertex normals
        in_uv_config : dict
            UV texture configuration
        mat_name : str
            Material name for the mesh
        """
        if not self.loaded:
            logger.warning("Pattern is not yet loaded. Nothing saved")
            return

        uv_config = {  # Defaults
            "seam_width": 0.5,
            "dpi": 600,
            "fabric_grain_texture_path": None,
            "fabric_grain_resolution": 1,
        }
        # Update with incoming values, if any
        uv_config.update(in_uv_config)

        uvs = texture_mesh_islands(
            texture_coords=np.array(self.vertex_texture),
            face_texture_coords=np.array(
                [
                    [tex_id0, tex_id1, tex_id2]
                    for _, tex_id0, _, tex_id1, _, tex_id2, in self.faces_with_texture
                ]
            ),
            out_texture_image_path=self.paths.g_texture,
            out_fabric_tex_image_path=self.paths.g_texture_fabric,
            out_mtl_file_path=self.paths.g_mtl,
            boundary_width=uv_config["seam_width"],
            dpi=uv_config["dpi"],
            background_img_path=uv_config["fabric_grain_texture_path"],
            background_resolution=uv_config["fabric_grain_resolution"],
            mat_name=mat_name,
        )
        save_obj(
            self.paths.g_box_mesh,
            self.vertices,
            self.faces_with_texture,
            uvs,
            vert_normals=self.eval_vertex_normals() if with_normals else None,
            mtl_file_name=self.paths.g_mtl.name,
            mat_name=mat_name,
        )

    def save_segmentation(self) -> None:
        """
        Store the self.stitch_segmentation list as a txt file.
        """
        if not self.loaded:
            logger.warning("Pattern is not yet loaded. Nothing saved")
            return

        rows = self.stitch_segmentation
        with open(self.paths.g_mesh_segmentation, "w") as file:
            for row in rows:
                # row is always a list now, convert entries to strings and join with comma
                row_data = ",".join(str(entry) for entry in row)
                # Write the row to the file
                file.write(row_data + "\n")

    def save_orig_lens(self) -> None:
        """
        Store the self.orig_lens dict as a pickle file.
        Self.orig_lens is a dict indexed by two global vertex indices and contains the ground truth length
        between those vertices in their 2D setting.
        """
        if not self.loaded:
            logger.warning("Pattern is not yet loaded. Nothing saved")
            return

        with open(self.paths.g_orig_edge_len, "wb") as file:
            pickle.dump(self.orig_lens, file)

    def serialize(  # type: ignore[override]
        self,
        paths: PathCofig,
        tag: str = "",
        with_3d: bool = False,
        with_text: bool = False,
        view_ids: bool = False,
        empty_ok: bool = False,
        with_v_norms: bool = False,
        store_panels: bool = False,
        uv_config: dict = {},
    ) -> str:
        """
        Store (annotated) visualisations (png,svg) of the pattern, the box mesh as an .obj file,
        the segmentation as a .txt file and the ground truth lengths dict as a .pickle file by overloading
        the serialize function of core.VisPattern.

        Parameters
        ----------
        paths : PathCofig
            Path configuration object
        tag : str
            Tag to append to filenames
        with_3d : bool
            If True, stores the pattern in 3d
        with_text : bool
            If True, stores visualisations with text
        view_ids : bool
            If True, shows IDs in visualisations
        empty_ok : bool
            If True, allows saving empty patterns
        with_v_norms : bool
            If True, includes vertex normals
        store_panels : bool
            If True, stores individual panel meshes
        uv_config : dict
            UV texture configuration

        Returns
        -------
        str
            Path to the output directory
        """
        if not self.loaded:
            logger.warning("Pattern is not yet loaded. Nothing saved")
            return ""

        self.paths = paths
        log_dir = super().serialize(
            self.paths.out_el,
            to_subfolder=False,
            tag=tag,
            with_3d=with_3d,
            with_text=with_text,
            view_ids=view_ids,
            empty_ok=empty_ok,
        )

        if store_panels:
            # Store panel
            for panel in self.panels.values():
                folder_path = Path(log_dir) / "panels"
                panel.save_panel_mesh_obj(folder_path)
            logger.info(f"Stored panels to {folder_path}...")

        self.save_box_mesh_obj(with_normals=with_v_norms, in_uv_config=uv_config)
        self.save_segmentation()
        self.save_orig_lens()
        self.save_vertex_labels()

        # Copy yaml files
        if self.paths.in_design_params.exists():
            shutil.copy(self.paths.in_design_params, self.paths.design_params)
        else:
            logger.warning(f"Path does not exist: {self.paths.in_design_params}")
        if self.paths.in_body_mes.exists():
            shutil.copy(self.paths.in_body_mes, self.paths.body_mes)
        else:
            logger.warning(f"Path does not exist: {self.paths.in_body_mes}")

        return str(log_dir)

