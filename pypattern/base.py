from abc import ABC, abstractmethod
import numpy as np

from pypattern.connector import Stitches


class BaseComponent(ABC):
    """Basic interface for garment-related components
    
        NOTE: modifier methods return self object to allow chaining of the
        operations
    """

    def __init__(self, name) -> None:
        self.name = name

        # List or dictionary of the interfaces of this components
        # available for connectivity with other components
        self.interfaces = {}

        # Rules for connecting subcomponents
        self.stitching_rules = Stitches()

    # Info
    def pivot_3D(self):
        """Pivot location of a component in 3D"""
        return [0, 0, 0]

    def bbox(self):
        """Bounding box -- in 2D"""
        return np.array([0, 0]), np.array([0, 0])

    def bbox3D(self):
        """Bounding box in 3D space"""
        return np.array([0, 0, 0]), np.array([0, 0, 0])

    def is_self_intersecting(self):
        """Check whether the component have self-intersections"""
        return False

    # Operations
    @abstractmethod
    def translate_by(self, delta_translation):
        return self

    @abstractmethod
    def translate_to(self, new_translation):
        """Set panel translation to be exactly that vector"""
        return self

    @abstractmethod
    def rotate_by(self, delta_rotation):
        return self

    @abstractmethod
    def rotate_to(self, new_rot):
        return self

    @abstractmethod
    def assembly(self, *args, **kwargs):
        pass

    # ----- Placement routines: these are the same for panels and components
    def place_below(self, comp, gap=2):
        """Place below the provided component"""
        other_bbox = comp.bbox3D()
        curr_bbox = self.bbox3D()

        self.translate_by([0, other_bbox[0][1] - curr_bbox[1][1] - gap, 0])
        return self

    def place_by_interface(self, self_interface, out_interface, gap=2):
        """Adjust the placement of component according to the connectivity
        instruction
        """
        
        # Align translation
        self_bbox = self_interface.bbox_3d()
        out_bbox = out_interface.bbox_3d()
        mid_out = (out_bbox[1] + out_bbox[0]) / 2
        mid_self = (self_bbox[1] + self_bbox[0]) / 2

        # Add a gap outside the current
        full_bbox = self.bbox3D()
        center = (full_bbox[0] + full_bbox[1]) / 2
        gap_dir = mid_self - center
        gap_dir = gap * gap_dir / np.linalg.norm(gap_dir)
        
        diff = mid_out - (mid_self + gap_dir)
        
        self.translate_by(diff)

        # NOTE: Norm evaluation of vertex set will fail 
        # for the alignment of 2D panels, where they are likely
        # to be in one line or in a panel plane instead of 
        # the interface place -- so I'm not using norms for gap estimation

        # TODO Estimate rotation
        # TODO not just placement by the midpoint of the interfaces?
        # It created a little overlap when both interfaces are angled a little differently
        return self


