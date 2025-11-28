"""Pattern specification data structures.

This module provides typed data classes for pattern specifications,
replacing dictionary-based access with proper classes and enums.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

import numpy as np


class CurvatureType(StrEnum):
    """Enumeration of supported edge curvature types."""

    QUADRATIC = "quadratic"
    CUBIC = "cubic"
    CIRCLE = "circle"


@dataclass
class CurvatureSpec:
    """Specification for edge curvature.

    Attributes
    ----------
    type : CurvatureType
        Type of curvature curve
    params : list[list[float]] | list[float]
        Parameters for the curvature:
        - For quadratic/cubic: list of control point coordinates (relative)
        - For circle: [radius, large_arc (0/1), right (0/1)]
    """

    type: CurvatureType
    params: list[list[float]] | list[float]

    @classmethod
    def from_dict(cls, data: dict) -> "CurvatureSpec":
        """Create CurvatureSpec from dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with 'type' and 'params' keys

        Returns
        -------
        CurvatureSpec
            Initialized curvature specification
        """
        return cls(
            type=CurvatureType(data["type"]),
            params=data["params"],
        )

    @classmethod
    def from_legacy_list(cls, data: list[float]) -> "CurvatureSpec":
        """Create CurvatureSpec from legacy list format (backward compatibility).

        Parameters
        ----------
        data : list[float]
            List of two floats representing quadratic control point

        Returns
        -------
        CurvatureSpec
            Initialized curvature specification as quadratic
        """
        return cls(
            type=CurvatureType.QUADRATIC,
            params=[data],
        )


@dataclass
class EdgeSpec:
    """Specification for a panel edge.

    Attributes
    ----------
    endpoints : tuple[int, int]
        Indices of start and end vertices in panel vertices list
    curvature : Optional[CurvatureSpec]
        Optional curvature specification for curved edges
    label : str
        Optional label for the edge (e.g., 'crotch_point_seam')
    """

    endpoints: tuple[int, int]
    curvature: Optional[CurvatureSpec] = None
    label: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "EdgeSpec":
        """Create EdgeSpec from dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with 'endpoints' and optionally 'curvature' and 'label'

        Returns
        -------
        EdgeSpec
            Initialized edge specification
        """
        curvature = None
        if "curvature" in data:
            if isinstance(data["curvature"], list):
                # Legacy format: list of floats
                curvature = CurvatureSpec.from_legacy_list(data["curvature"])
            else:
                # New format: dict with type and params
                curvature = CurvatureSpec.from_dict(data["curvature"])

        return cls(
            endpoints=tuple(data["endpoints"]),
            curvature=curvature,
            label=data.get("label", ""),
        )


@dataclass
class PanelSpec:
    """Specification for a pattern panel.

    Attributes
    ----------
    translation : np.ndarray
        3D translation vector [x, y, z]
    rotation : np.ndarray
        3D rotation vector (Euler angles) [x, y, z]
    vertices : list[list[float]]
        List of 2D vertex coordinates [[x1, y1], [x2, y2], ...]
    edges : list[EdgeSpec]
        List of edge specifications forming the panel boundary
    label : str
        Optional label for the panel (e.g., 'body', 'leg', 'arm')
    """

    translation: np.ndarray
    rotation: np.ndarray
    vertices: list[list[float]]
    edges: list[EdgeSpec]
    label: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PanelSpec":
        """Create PanelSpec from dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with 'translation', 'rotation', 'vertices', 'edges',
            and optionally 'label'

        Returns
        -------
        PanelSpec
            Initialized panel specification
        """
        return cls(
            translation=np.asarray(data["translation"]),
            rotation=np.asarray(data["rotation"]),
            vertices=data["vertices"],
            edges=[EdgeSpec.from_dict(edge) for edge in data["edges"]],
            label=data.get("label", ""),
        )


@dataclass
class StitchSideSpec:
    """Specification for one side of a stitch.

    Attributes
    ----------
    panel : str
        Name of the panel containing this edge
    edge : int
        Index of the edge in the panel's edges list
    """

    panel: str
    edge: int

    @classmethod
    def from_dict(cls, data: dict) -> "StitchSideSpec":
        """Create StitchSideSpec from dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with 'panel' and 'edge' keys

        Returns
        -------
        StitchSideSpec
            Initialized stitch side specification
        """
        return cls(
            panel=data["panel"],
            edge=data["edge"],
        )


@dataclass
class StitchSpec:
    """Specification for a stitch connecting two panel edges.

    Attributes
    ----------
    side_0 : StitchSideSpec
        First side of the stitch
    side_1 : StitchSideSpec
        Second side of the stitch
    right_wrong : bool
        Whether this is a right-to-wrong side stitch (default: False)
    """

    side_0: StitchSideSpec
    side_1: StitchSideSpec
    right_wrong: bool = False

    @classmethod
    def from_list(cls, data: list) -> "StitchSpec":
        """Create StitchSpec from list format.

        Parameters
        ----------
        data : list
            List with two dicts for sides, optionally followed by 'right_wrong' string

        Returns
        -------
        StitchSpec
            Initialized stitch specification
        """
        right_wrong = len(data) == 3 and data[2] == "right_wrong"

        return cls(
            side_0=StitchSideSpec.from_dict(data[0]),
            side_1=StitchSideSpec.from_dict(data[1]),
            right_wrong=right_wrong,
        )


@dataclass
class PatternSpec:
    """Complete pattern specification.

    Attributes
    ----------
    panels : dict[str, PanelSpec]
        Dictionary mapping panel names to their specifications
    stitches : list[StitchSpec]
        List of stitch specifications
    panel_order : Optional[list[str]]
        Optional ordered list of panel names
    """

    panels: dict[str, PanelSpec]
    stitches: list[StitchSpec]
    panel_order: Optional[list[str]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PatternSpec":
        """Create PatternSpec from dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with 'panels' and 'stitches' keys,
            optionally 'panel_order'

        Returns
        -------
        PatternSpec
            Initialized pattern specification
        """
        panels = {
            name: PanelSpec.from_dict(panel_data)
            for name, panel_data in data["panels"].items()
        }

        stitches = []
        if "stitches" in data:
            stitches = [StitchSpec.from_list(stitch_data) for stitch_data in data["stitches"]]

        return cls(
            panels=panels,
            stitches=stitches,
            panel_order=data.get("panel_order"),
        )

