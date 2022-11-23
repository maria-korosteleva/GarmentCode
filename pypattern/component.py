
from typing import Any

class Component():
    """Garment element (or whole piece) composed of simpler connected garment elements"""

    def __init__(self) -> None:
        pass

    def assembly(self):
        """Construction process of the garment component
        
        Returns: simulator friendly descriptuin of component sewing pattern
        """
        pass

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.assembly(*args,**kwds)
