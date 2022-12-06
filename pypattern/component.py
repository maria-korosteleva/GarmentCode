
# Custom
# TODO some elements of spec template should probably be optional?
# TODO move spec template here?
from pattern.core import BasicPattern
from .connector import connect
from .base import BaseComponent

class Component(BaseComponent):
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    def __init__(self, name) -> None:
        super().__init__(name)

        self.subs = []  # list of generative sub-components

        # rules for connecting sub-components of this component
        # TODO stitching rules should allow modification of sub components
        self.stitching_rules = []

    # Operations -- update object in-place
    # All return self object to allow chained operations
    def translate_by(self, delta_vector):
        """Translate component by a vector"""
        for subs in self._get_subcomponents():
            subs.translate_by(delta_vector)
        return self

    def rotate_by(self, delta_rotation):
        """Rotate component by a given rotation"""
        for subs in self._get_subcomponents():
            subs.rotate(delta_rotation)
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
        spattern = BasicPattern()
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

        for rule in self.stitching_rules:
            spattern.pattern['stitches'].append(connect(rule[0], rule[1]))

        # TODO Normalize pattern (edge loops, etc.)?
        return spattern   

    # Utilities
    def _get_subcomponents(self):
        """Unique set of subcomponents defined in the self.subs list or as attributes of the object"""

        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']
        return list(set([att for att in all_attrs if isinstance(att, BaseComponent)] + self.subs))


