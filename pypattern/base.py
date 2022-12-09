
from typing import Any
from .connector import Stitches

class BaseComponent():
    """Basic interface for garment-related components"""

    def __init__(self, name) -> None:
        self.name = name

        # List of the interfaces of this components
        # available for connectivity with other components
        self.interfaces = []

        # Rules for connecting subcomponents
        self.stitching_rules = Stitches()

    def translate_by(self, delta_translation):
        pass

    def rotate_by(self, delta_rotation):
        pass

    def assembly(self, *args,**kwds):
        return {}

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.assembly(*args,**kwds)