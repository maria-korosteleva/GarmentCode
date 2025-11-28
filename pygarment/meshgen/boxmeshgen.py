"""Legacy compatibility shim for boxmeshgen module.

This module has been refactored and split into multiple files under pygarment.meshgen.box_mesh_gen.
All imports are redirected to the new location for backward compatibility.
"""

# Redirect all imports to the new location
from pygarment.meshgen.box_mesh_gen import (
    BoxMesh,
    Edge,
    Panel,
    Seam,
    PatternLoadingError,
    MultiStitchingError,
    StitchingError,
    DegenerateTrianglesError,
    NormError,
)

__all__ = [
    "BoxMesh",
    "Edge",
    "Panel",
    "Seam",
    "PatternLoadingError",
    "MultiStitchingError",
    "StitchingError",
    "DegenerateTrianglesError",
    "NormError",
]
