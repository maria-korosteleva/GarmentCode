"""Box mesh generation module.

This module provides classes for generating box meshes from pattern specifications.
"""

from pygarment.meshgen.box_mesh_gen.errors import (
    PatternLoadingError,
    MultiStitchingError,
    StitchingError,
    DegenerateTrianglesError,
    NormError,
)
from pygarment.meshgen.box_mesh_gen.panel import Panel
from pygarment.meshgen.box_mesh_gen.edge import Edge
from pygarment.meshgen.box_mesh_gen.seam import Seam
from pygarment.meshgen.box_mesh_gen.box_mesh import BoxMesh

__all__ = [
    "PatternLoadingError",
    "MultiStitchingError",
    "StitchingError",
    "DegenerateTrianglesError",
    "NormError",
    "Panel",
    "Edge",
    "Seam",
    "BoxMesh",
]

