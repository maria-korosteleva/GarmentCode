import numpy as np
from scipy.spatial.transform import Rotation as R

# Custom
from pattern.wrappers import VisPattern
from .base import BaseComponent

class Component(BaseComponent):
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    # TODOLOW Overload copy -- respecting edge sequences -- never had any problems though

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

    def is_self_intersecting(self):
        """Check whether the component have self-intersections on panel level"""

        for s in self._get_subcomponents():
            if s.is_self_intersecting():
                return True
        return False

    # Subcomponents
    def _get_subcomponents(self):
        """Unique set of subcomponents defined in the self.subs list or as attributes of the object"""

        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']
        return list(set([att for att in all_attrs if isinstance(att, BaseComponent)] + self.subs))

