"""Shortcuts for common operations on panels and components"""

from copy import deepcopy
from scipy.spatial.transform import Rotation as R

# Custom 
from .component import Component


def distribute_Y(component: Component, n_copies: int):
    """Distribute copies of component over the circle around Oy"""
    copies = [ component ]
    for i in range(n_copies - 1):
        new_component = deepcopy(copies[-1])
        new_component.name = f'panel_{i}'   # Unique
        delta_rotation = R.from_euler('XYZ', [0, 360 / n_copies, 0], degrees=True)

        new_component.rotate_by(delta_rotation)
        new_component.translation = delta_rotation.apply(new_component.translation)

        copies.append(new_component)

    return copies