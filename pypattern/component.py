import numpy as np
from scipy.spatial.transform import Rotation as R

# Custom
from pattern.core import BasicPattern
from pattern.wrappers import VisPattern
from .base import BaseComponent
from .interface import Interface

class Component(BaseComponent):
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    # TODO Overload copy -- respecting edge sequences

    def __init__(self, name) -> None:
        super().__init__(name)

        self.subs = []  # list of generative sub-components

    # Operations -- update object in-place
    # All return self object to allow chained operations

    # Placements
    def pivot_3D(self):
        """Pivot of a component as a block

            NOTE: The relation of pivots of subblocks needs to be 
            preserved in any placement operations on components
        """
        mins, maxes = self.bbox3D()

        return np.array(((mins[0] + maxes[0]) / 2, maxes[1], (mins[-1] + maxes[-1]) / 2))

    def translate_by(self, delta_vector):
        """Translate component by a vector"""
        for subs in self._get_subcomponents():
            subs.translate_by(delta_vector)
        return self
    
    def translate_to(self, new_translation):
        """Set panel translation to be exactly that vector"""
        pivot = self.pivot_3D()
        for subs in self._get_subcomponents():
            sub_pivot = subs.pivot_3D()
            subs.translate_to(np.asarray(new_translation) + (sub_pivot - pivot))
        return self

    def rotate_by(self, delta_rotation:R):
        """Rotate component by a given rotation"""
        pivot = self.pivot_3D()
        for subs in self._get_subcomponents():
            # With preserving relationships between components
            rel = subs.pivot_3D() - pivot
            rel_rotated = delta_rotation.apply(rel) 
            subs.rotate_by(delta_rotation)
            subs.translate_by(rel_rotated - rel)
        return self
    
    def rotate_to(self, new_rot):
        # TODOLOW Implement with correct preservation of relative placement
        # of subcomponents
        raise NotImplementedError(
            f'Component::Error::rotate_to is not supported on component level.'
            'Use relative <rotate_by()> method instead')

    def place_below(self, comp: BaseComponent, gap=2):
        """Place below the provided component"""
        other_bbox = comp.bbox3D()
        curr_bbox = self.bbox3D()

        self.translate_by([0, other_bbox[0][1] - curr_bbox[1][1] - gap, 0])

        return self

    def place_by_interface(self, 
                            self_interface:Interface, 
                            out_interface:Interface, 
                            gap=2):
        """Adjust the placement of component acconding to the connectivity instuction        
        """
        
        # Alight translation
        self_verts = self_interface.verts_3d()
        out_verts = out_interface.verts_3d()
        mid_out = np.mean(out_verts, axis=0)
        mid_self = np.mean(self_verts, axis=0)

        # Add a gap outside of the current 
        bbox = self.bbox3D()
        center = (bbox[0] + bbox[1]) / 2
        gap_dir = mid_self - center
        gap_dir = gap * gap_dir / np.linalg.norm(gap_dir)
        
        diff = mid_out - (mid_self + gap_dir)

        self.translate_by(diff)

        # NOTE: Norm evaluation of vertex set will fail 
        # for the alignment of 2D panels, where they are likely
        # to be in one line or in a panel plane instead of 
        # the interface place -- so I'm not using norms for gap esitmation

        # TODO Estimate rotation
        # TODO not just placement by the midpoint of the interfaces?

        return self

    # Mirror
    def mirror(self, axis=[0, 1]):
        """Swap this component with it's mirror image by recursively mirroring sub-components
        
            Axis specifies 2D axis to swap around: Y axis by default
        """
        for subs in self._get_subcomponents():
            subs.mirror(axis)
        return self

    # Build the component -- get serializable representation
    def assembly(self):
        """Construction process of the garment component
        
        Returns: simulator friendly description of component sewing pattern
        """
        spattern = VisPattern()
        spattern.name = self.name

        subs = self._get_subcomponents()
        if not subs:
            return spattern

        # Simple merge of sub-component representations
        for sub in subs:
            sub_raw = sub().pattern

            # simple merge of panels
            spattern.pattern['panels'] = {**spattern.pattern['panels'], **sub_raw['panels']}

            # of stitches
            spattern.pattern['stitches'] += sub_raw['stitches']

        spattern.pattern['stitches'] += self.stitching_rules.assembly()

        return spattern   

    # Utilities
    def bbox3D(self):
        """Evaluate 3D bounding box of the current component"""
        
        subs = self._get_subcomponents()
        bboxes = [s.bbox3D() for s in subs]

        mins = np.vstack([b[0] for b in bboxes])
        maxes = np.vstack([b[1] for b in bboxes])

        return mins.min(axis=0), maxes.max(axis=0)

    # Subcomponents
    def _get_subcomponents(self):
        """Unique set of subcomponents defined in the self.subs list or as attributes of the object"""

        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']
        return list(set([att for att in all_attrs if isinstance(att, BaseComponent)] + self.subs))

