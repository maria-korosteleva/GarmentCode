"""Data structures for passing in-memory garment data to simulation."""

from dataclasses import dataclass
from typing import Any, Optional
import numpy as np

from pattern_definitions.body_definition import BodyDefinition
from pygarment.meshgen.boxmeshgen import BoxMesh


@dataclass
class GarmentData:
    """
    Container for in-memory garment and body data to avoid disk I/O.
    
    This class holds all the data structures needed by Cloth.build_stage()
    that would otherwise be read from disk. When provided, Cloth will use
    this data directly instead of reading from files.
    
    Attributes
    ----------
    box_mesh : BoxMesh
        Loaded BoxMesh object containing the garment mesh data.
        Must have been loaded (box_mesh.loaded == True) before use.
    body_definition : BodyDefinition
        Body definition object for accessing body measurements and parameters.
    body_vertices : np.ndarray
        Body mesh vertices (Nx3 array).
    body_indices : np.ndarray
        Body mesh indices (flattened array for Warp).
    body_faces : np.ndarray
        Body mesh faces (Mx3 array).
    body_segmentation : dict
        Body segmentation dictionary (from JSON file).
    vertex_labels : dict, optional
        Vertex labels dictionary mapping label names to vertex indices.
        If None, will be loaded from file or extracted from BoxMesh.
    """
    box_mesh: BoxMesh
    body_definition: BodyDefinition
    body_vertices: np.ndarray
    body_indices: np.ndarray
    body_faces: np.ndarray
    body_segmentation: dict[str, Any]
    vertex_labels: Optional[dict[str, list[int]]] = None
    
    def __post_init__(self):
        """Validate that BoxMesh is loaded."""
        if not self.box_mesh.loaded:
            raise ValueError("BoxMesh must be loaded (call box_mesh.load()) before creating GarmentData")

