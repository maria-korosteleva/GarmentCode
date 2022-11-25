
from typing import Any
import copy

# Custom
# TODO some elements of spec template should probably be optional?
# TODO move spec template here?
from pattern.core import pattern_spec_template

class Component():
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    def __init__(self, name) -> None:
        self.name = name

        # Edges of special type that describe the way pattern geometry is 
        # connected to other panels 
        self.interfaces = []

    def assembly(self):
        """Construction process of the garment component
        
        Returns: simulator friendly descriptuin of component sewing pattern
        """
        # TODO default subcomponent assembly
        # subs = self._get_subcomponents()
        #if not subs:
            
        return copy.deepcopy(pattern_spec_template)

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.assembly(*args,**kwds)

    # Utilities
    def _get_subcomponents(self):
        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']

        return [att for att in all_attrs if isinstance(att, Component)]


