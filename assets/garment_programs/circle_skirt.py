# Custom
import pypattern as pyp
from scipy.spatial.transform import Rotation as R
import numpy as np

# other assets
from .bands import WB

class SkirtCircle(pyp.Panel):
    """One panel circle skirt"""

    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['flare-skirt']

        waist = body['waist']
        suns = design['suns']['v']

        # TODO Should be part of smart parameters evaluation
        length = body['hips_line'] + design['length']['v'] * (body['waist_level'] - body['hips_line'])

        waist_rad = waist / (suns * 2 * np.pi)
        halfarc = suns * np.pi


        dist_w = 2 * waist_rad * np.sin(halfarc)
        dist_out = 2 * (waist_rad + length) * np.sin(halfarc)

        vert_len = length * np.cos(halfarc)


        self.edges.append(pyp.CircleEdge(
            [-dist_w/2, 0], [dist_w/2, 0], radius=waist_rad))
        self.edges.append(pyp.Edge(self.edges[-1].end, [dist_out / 2, -vert_len]))
        self.edges.append(pyp.CircleEdge(
            self.edges[-1].end, [- dist_out / 2, -vert_len], radius=waist_rad + length))
        self.edges.close_loop()