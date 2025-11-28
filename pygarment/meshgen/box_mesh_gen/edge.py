"""Edge representation for box mesh generation."""

import math
from typing import Optional

import numpy as np
import svgpathtools as svgpath
from loguru import logger

import pygarment.pattern.utils as pat_utils
from pygarment.meshgen.box_mesh_gen.seam import Seam
from pygarment.meshgen.pattern_spec import EdgeSpec, CurvatureType


class Edge:
    """
    Represents an edge of a panel.

    Parameters
    ----------
    edge_spec : EdgeSpec
        Edge specification containing endpoints, curvature, and label
    vertices : np.ndarray
        Panel corner vertices array
    mesh_resolution : float
        Mesh resolution for vertex spacing along edges
    """

    def __init__(
        self,
        edge_spec: EdgeSpec,
        vertices: np.ndarray,
        mesh_resolution: float,
    ) -> None:
        self.endpoints = vertices[list(edge_spec.endpoints)]
        self.stitch_ref: Optional["Seam"] = None
        self.n_edge_verts = -1
        self.curve: Optional[svgpath.Path] = None
        self.init_curve(edge_spec, mesh_resolution)
        self.vertex_range: list[int] = []
        self.label = edge_spec.label

    def init_curve(
        self,
        edge_spec: EdgeSpec,
        mesh_resolution: float,
    ) -> None:
        """
        Initialize curve object (svgpathtools) and set the number
        of vertices on the edge (n_edge_verts) depending
        on the mesh_resolution (= 1.0 => Vertices are spread with distance ~1.0 cm).

        Parameters
        ----------
        edge_spec : EdgeSpec
            Edge specification containing curvature information
        mesh_resolution : float
            Mesh resolution for vertex spacing
        """
        start, end = self.endpoints

        if edge_spec.curvature is not None:
            curvature = edge_spec.curvature
            if curvature.type == CurvatureType.QUADRATIC:
                # Handle both legacy list format and new format
                params = curvature.params
                control_scale: list[float]
                if isinstance(params, list):
                    if len(params) > 0 and isinstance(params[0], list):
                        # New format: list of lists
                        control_scale = params[0]  # type: ignore[assignment]
                    elif len(params) == 2 and all(isinstance(x, (int, float)) for x in params):
                        # Legacy format: single list of two floats
                        control_scale = params  # type: ignore[assignment]
                    else:
                        raise ValueError(f"Invalid quadratic curvature params: {params}")
                else:
                    raise ValueError(f"Invalid quadratic curvature params: {params}")
                control_point = pat_utils.rel_to_abs_2d(start, end, control_scale)
                self.curve = svgpath.QuadraticBezier(*pat_utils.list_to_c([start, control_point, end]))

            elif curvature.type == CurvatureType.CIRCLE:
                # https://svgwrite.readthedocs.io/en/latest/classes/path.html#svgwrite.path.Path.push_arc
                params = curvature.params
                if isinstance(params, list) and len(params) == 3:
                    radius_val, large_arc_val, right_val = params
                    # Ensure radius is a float
                    if isinstance(radius_val, list):
                        raise ValueError(f"Invalid circle radius (got list): {radius_val}")
                    radius = float(radius_val)
                    large_arc = bool(large_arc_val)
                    right = bool(right_val)
                else:
                    raise ValueError(f"Invalid circle curvature params: {params}")

                self.curve = svgpath.Arc(
                    pat_utils.list_to_c(start),
                    complex(radius, radius),  # radius + 1j * radius
                    rotation=0,
                    large_arc=large_arc,
                    sweep=right,  # maya: not right
                    end=pat_utils.list_to_c(end),
                )

            elif curvature.type == CurvatureType.CUBIC:
                cps = []
                params = curvature.params
                if isinstance(params, list) and len(params) > 0:
                    if isinstance(params[0], list):
                        # List of control points
                        for p in params:
                            control_point = pat_utils.rel_to_abs_2d(start, end, p)
                            cps.append(control_point)
                    else:
                        raise ValueError(f"Invalid cubic curvature params: {params}")
                else:
                    raise ValueError(f"Invalid cubic curvature params: {params}")

                self.curve = svgpath.CubicBezier(*pat_utils.list_to_c([start, *cps, end]))

            else:
                raise NotImplementedError(
                    f"{self.__class__.__name__}::Unknown curvature type {curvature.type}"
                )

        else:
            self.curve = svgpath.Line(*pat_utils.list_to_c([start, end]))

        edgelength = self.curve.length()
        res = mesh_resolution
        n_edge_verts = math.ceil(edgelength / res) + 1

        self.n_edge_verts = n_edge_verts

        if n_edge_verts == 2 and res > 1.0:
            logger.warning(
                f"Detected edge represented only by two vertices. "
                f"Mesh resolution might be too low. Resolution = {res}, edge length = {edgelength}"
            )

    def set_vertex_range(self, start_idx: int, begin_in: int, end_in: int, end_idx: int) -> None:
        """
        Set the vertex range of the current edge in the context of a panel.

        The vertex range contains the indices into panel_vertices, defining the edge vertices with
        respect to the panel_vertices.

        Parameters
        ----------
        start_idx : int
            Index of edge.start into panel_vertices
        begin_in : int
            Index of 2nd edge vertex into panel_vertices
        end_in : int
            Index + 1 of second to last edge vertex into panel_vertices
        end_idx : int
            Index of edge.end into panel_vertices
        """
        self.vertex_range = [start_idx] + list(range(begin_in, end_in)) + [end_idx]

    def as_curve(self, absolute: bool = True) -> svgpath.Path:
        """
        Return curve as a svgpath curve object.

        Converting on the fly as exact vertex location might have been updated since
        the creation of the edge.

        Parameters
        ----------
        absolute : bool
            True if correct start and end edge vertices are processed
            else use start = [0,0] and end = [1,0]

        Returns
        -------
        svgpath.Path
            Either correct curve or approximation
        """
        if absolute:
            # Return correct curve
            return self.curve

        if self.curve is None:
            raise ValueError("Curve is not initialized")

        cp = [pat_utils.c_to_np(c) for c in self.curve.bpoints()[1:-1]]
        nodes = np.vstack(([0, 0], cp, [1, 0]))
        params = nodes[:, 0] + 1j * nodes[:, 1]
        return svgpath.QuadraticBezier(*params) if len(cp) < 2 else svgpath.CubicBezier(*params)

    def linearize(self, panel_vertices: list[np.ndarray]) -> list:
        """
        Return the current edge (self) as a sequence of lines.

        Parameters
        ----------
        panel_vertices : list[np.ndarray]
            Panel object containing panel_vertices

        Returns
        -------
        list
            List of vertices (start and end vertices of corresponding line)
            characterizing the current edge (self)
        """
        if isinstance(self.curve, svgpath.Line):
            return [self.endpoints]
        else:
            v_range = self.vertex_range
            edge_vertices = np.array(panel_vertices)[v_range]
            edge_seq = []
            for i in range(len(edge_vertices) - 1):
                pair = [edge_vertices[i], edge_vertices[i + 1]]
                edge_seq.append(pair)
            return edge_seq

