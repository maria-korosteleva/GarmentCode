from abc import ABC, abstractmethod
import numpy as np

from pygarment.garmentcode.connector import Stitches


class BaseComponent(ABC):
    """Basic interface for garment-related components
    
        NOTE: modifier methods return self object to allow chaining of the
        operations
    """

    def __init__(self, name, verbose=False) -> None:
        self.name = name
        self.verbose = verbose

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

    def place_by_interface(
            self, 
            self_interface, 
            out_interface, 
            gap=2, 
            alignment='center',
            gap_dir=None
        ):
        """Adjust the placement of component according to the connectivity
        instruction

        Alignment options: 
        'center' center of the interface to center of the interface
        'top' - top on Y axis
        'bottom' - bottom on Y axis
        'left' - left on X axis
        'right' - right on X axis
        """
        
        # Align translation
        self_bbox = self_interface.bbox_3d()
        out_bbox = out_interface.bbox_3d()
        
        # Determine alignment point depending on requested alignment type
        point_out = (out_bbox[1] + out_bbox[0]) / 2
        point_self = (self_bbox[1] + self_bbox[0]) / 2
        if alignment == 'center':
            pass # No modification needed
        elif alignment == 'top':
            point_out[1] = out_bbox[1][1]  # Use max in Y
            point_self[1] = self_bbox[1][1]
        elif alignment == 'bottom':
            point_out[1] = out_bbox[0][1]  # Use min in Y
            point_self[1] = self_bbox[0][1]
        elif alignment == 'right':
            point_out[0] = out_bbox[0][0]  # Use min in X
            point_self[0] = self_bbox[0][0]
        elif alignment == 'left':
            point_out[0] = out_bbox[1][0]  # Use max in X
            point_self[0] = self_bbox[1][0]
        else: 
            raise ValueError(
                f'{self.__class__.__name__}::{self.name}::ERROR::'
                f'Uknown alignment type ({alignment}) requested in place_by_interface().'
                f' Available types: center, top, bottom, left, right')

        # Add a gap outside the current
        if gap_dir is None:
            full_bbox = self.bbox3D()
            center = (full_bbox[0] + full_bbox[1]) / 2
            mid_self = (self_bbox[1] + self_bbox[0]) / 2
            gap_dir = mid_self - center
        
        gap_dir = gap * gap_dir / np.linalg.norm(gap_dir)
        diff = point_out - (point_self + gap_dir)
        
        self.translate_by(diff)

        # NOTE: Norm evaluation of vertex set will fail 
        # for the alignment of 2D panels, where they are likely
        # to be in one line or in a panel plane instead of 
        # the interface place -- so I'm not using norms for gap estimation

        # TODO Estimate rotation
        # TODO not just placement by the midpoint of the interfaces?
        # It created a little overlap when both interfaces are angled a little differently
        return self


