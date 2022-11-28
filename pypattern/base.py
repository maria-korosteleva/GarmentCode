
from typing import Any

class BaseComponent():
    """Basic interface for garment-related components"""

    def __init__(self, name) -> None:
        self.name = name

        # List of the interfaces of this components
        # available for connectivity with other components
        # NOTE interfaces only change the shape of a component if connected to something =) 
        self.interfaces = []

    def translate_by(self, delta_translation):
        pass

    def rotate_by(self, delta_rotation):
        pass

    def assembly(self, *args,**kwds):
        return {}

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.assembly(*args,**kwds)