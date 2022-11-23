
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

    # DRAFT
    def connect(self, panel1_raw, int_id1, panel2_raw, int_id2):
        name_1 = list(panel1_raw.keys())[0]
        name_2 = list(panel2_raw.keys())[0]

        # TODO What if connecting ids are not propagated?
        # Loop over edges again to find correspondance between logical and geometric
        # TODO OR!! Store the correspondance in the edge object when assembly is called O_o
        # In the panel or in the edge object itself O_o => Problem solved

        return [
                    {
                        'panel': name_1,  # corresponds to a name. 
                                                # Only one element of the first level is expected
                        'edge': panel1_raw[name_1]['connecting_ids'][int_id1]
                    },
                    {
                        'panel': name_2,
                        'edge': panel2_raw[name_2]['connecting_ids'][int_id2]
                    }
                ]

    # Utilities
    def _get_subcomponents(self):
        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']

        return [att for att in all_attrs if isinstance(att, Component)]