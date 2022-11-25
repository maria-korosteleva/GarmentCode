

import copy

# Custom
# TODO some elements of spec template should probably be optional?
# TODO move spec template here?
from pattern.core import pattern_spec_template
from .connector import connect
from .base import BaseComponent

class Component(BaseComponent):
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    def __init__(self, name) -> None:
        super().__init__(name)

        # rules for connecting sub-components of this component
        # TODO stitching rules should allow modification of sub components
        self.stitching_rules = []

    def assembly(self):
        """Construction process of the garment component
        
        Returns: simulator friendly description of component sewing pattern
        """
        base = copy.deepcopy(pattern_spec_template)

        subs = self._get_subcomponents()
        if not subs:
            return base

        # TODO Name collision for panels?
        # Simple merge of sub-component representations
        for sub in subs:
            sub_raw = sub()['pattern']

            # TODO use class for merges (or something)
            # simple merge of panels
            base['pattern']['panels'] = {**base['pattern']['panels'], **sub_raw['panels']}

            # of stitches
            base['pattern']['stitches'] += sub_raw['stitches']

        for rule in self.stitching_rules:
            base['pattern']['stitches'].append(connect(rule[0], rule[1]))

        return base   

    # Utilities
    def _get_subcomponents(self):
        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']

        return [att for att in all_attrs if isinstance(att, BaseComponent)]


