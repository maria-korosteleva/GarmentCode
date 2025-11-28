"""Seam representation for box mesh generation."""

from typing import Optional


class Seam:
    """
    Representation of a seam in a box mesh.

    Parameters
    ----------
    panel_1_name : str
        Name of the first panel
    edge_1 : int
        Edge index in the first panel
    panel_2_name : str
        Name of the second panel
    edge_2 : int
        Edge index in the second panel
    label : Optional[str]
        Label to assign to the seam on serialization (default: None)
    n_verts : Optional[int]
        Number of mesh vertices sampled for the seam (default: None, not sampled)
    swap : bool
        Define the edge swap for the edge pair. Default: True --
        swapped -- the end of one panel edge connects to the start vertex
        of the other panel edge
    """

    def __init__(
        self,
        panel_1_name: str,
        edge_1: int,
        panel_2_name: str,
        edge_2: int,
        label: Optional[str] = None,
        n_verts: Optional[int] = None,
        swap: bool = True,
    ) -> None:
        self.panel_1 = panel_1_name
        self.panel_2 = panel_2_name
        self.edge_1 = edge_1
        self.edge_2 = edge_2
        self.label = label

        # NOTE: default connection of stitches is edge1 end-> edge2 start
        # following manifold condition
        # => stitch right side to the right side of the fabric pieces
        self.swap = swap  # Default swap state connects right side to the right side of fabric

        self.n_verts = n_verts  # Number of mesh vertices

