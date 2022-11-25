
from typing import Any
import copy

# Custom
# TODO some elements of spec template should probably be optional?
# TODO move spec template here?
from pattern.core import pattern_spec_template
from .connector import InterfaceInstance

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
    # TODO this has nothing to do with component object, does it?
    def connect(self, int1:InterfaceInstance, int2:InterfaceInstance):
        # TODO What if connecting ids are not propagated?
        # Loop over edges again to find correspondance between logical and geometric
        # TODO OR!! Store the correspondance in the edge object when assembly is called O_o
        # In the panel or in the edge object itself O_o => Problem solved

        # TODO Multiple edges in the interface / geometric ids
        # TODO Interface containing geometric ids directly!!

        panel1 = int1.panel
        panel2 = int2.panel
        return [
                    {
                        'panel': panel1.name,  # corresponds to a name. 
                                                # Only one element of the first level is expected
                        'edge': panel1.edges[int1.edge_id].geometric_ids[0]  # TODO What if we only want part of the geometric ids?
                    },
                    {
                        'panel': panel2.name,
                        'edge': panel2.edges[int2.edge_id].geometric_ids[0]  # TODO What if we only want part of the geometric ids?
                    }
                ]

    # Utilities
    def _get_subcomponents(self):
        all_attrs = [getattr(self, name) for name in dir(self) if name[:2] != '__' and name[-2:] != '__']

        return [att for att in all_attrs if isinstance(att, Component)]