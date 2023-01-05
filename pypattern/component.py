
# Custom
# TODO some elements of spec template should probably be optional?
from pattern.core import BasicPattern
from pattern.wrappers import VisPattern
from .base import BaseComponent

class Component(BaseComponent):
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    # TODO Overload copy -- respecting edge sequences

    def __init__(self, name) -> None:
        super().__init__(name)

        self.subs = []  # list of generative sub-components

    # Operations -- update object in-place
    # All return self object to allow chained operations
    def translate_by(self, delta_vector):
        """Translate component by a vector"""
        for subs in self._get_subcomponents():
            subs.translate_by(delta_vector)
        return self
    
    def translate_to(self, new_translation):
        """Set panel translation to be exactly that vector"""
        for subs in self._get_subcomponents():
            subs.translate_to(new_translation)
        return self

    def rotate_by(self, delta_rotation):
        """Rotate component by a given rotation"""
        for subs in self._get_subcomponents():
            subs.rotate_by(delta_rotation)
        return self
    
    def rotate_to(self, new_rot):
        """Set panel rotation to be exactly given rotation"""
        for subs in self._get_subcomponents():
            subs.rotate_to(new_rot)
        return self

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
        spattern = VisPattern(view_ids=False)
        spattern.name = self.name

        subs = self._get_subcomponents()
        if not subs:
            return spattern

        # TODO Name collision for panels?
        # Simple merge of sub-component representations
        for sub in subs:
            sub_raw = sub().pattern

            # TODO use class for merges (or something)
            # simple merge of panels
            spattern.pattern['panels'] = {**spattern.pattern['panels'], **sub_raw['panels']}

            # of stitches
            spattern.pattern['stitches'] += sub_raw['stitches']

        spattern.pattern['stitches'] += self.stitching_rules.assembly()

        # TODO Normalize pattern (edge loops, etc.)?
        return spattern   

    # Utilities
    def _get_subcomponents(self):
        """Unique set of subcomponents defined in the self.subs list or as attributes of the object"""

        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']
        return list(set([att for att in all_attrs if isinstance(att, BaseComponent)] + self.subs))


