
from typing import Any
from .connector import Stitches

class BaseComponent():
    """Basic interface for garment-related components
    
        NOTE: modifier methods return self object to allow chaining of the operations
    """

    def __init__(self, name) -> None:
        self.name = name

        # List or dictionary of the interfaces of this components
        # available for connectivity with other components
        self.interfaces = []

        # Rules for connecting subcomponents
        self.stitching_rules = Stitches()

    def translate_by(self, delta_translation):
        return self

    def translate_to(self, new_translation):
        """Set panel translation to be exactly that vector"""
        return self

    def rotate_by(self, delta_rotation):
        return self
    
    def rotate_to(self, new_rot):
        return self

    def assembly(self, *args,**kwds):
        return {}

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.assembly(*args,**kwds)