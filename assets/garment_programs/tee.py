""" Panels for a straight upper garment (T-shirt)
    Note that the code is very similar to Bodice. 
"""

from copy import copy
import numpy as np

# Custom
import pygarment as pyg

class TorsoFrontHalfPanel(pyg.Panel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    def __init__(self, name, body, design) -> None:
        """ Front = True, provides the adjustments necessary for the front panel
        """
        super().__init__(name)

        design = design['shirt']
        # account for ease in basic measurements
        m_width = design['width']['v'] * body['bust']
        b_width = m_width

        # sizes 
        body_width = (body['bust'] - body['back_width']) / 2 
        frac = body_width / body['bust'] 
        self.width = frac * m_width
        b_width = frac * b_width
        connecting_point =  b_width * (m_width / 4 / self.width)

        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        length = design['length']['v'] * body['waist_line']

        # length in the front panel is adjusted due to shoulder inclination
        # for the correct sleeve fitting
        fb_diff = (frac - (0.5 - frac)) * body['bust']
        length = length - sh_tan * fb_diff

        self.edges = pyg.esf.from_verts(
            [0, 0], 
            [-connecting_point, 0],   # Extra vertex to connect with front-back symmetric bottoms correctly
            [-b_width, 0], 
            [-self.width, length], 
            [0, length + shoulder_incl], 
            loop=True
        )

        # Interfaces
        self.interfaces = {
            'outside':  pyg.Interface(self, self.edges[2]),   
            'inside': pyg.Interface(self, self.edges[-1]),
            'shoulder': pyg.Interface(self, self.edges[-2]),
            'bottom_front': pyg.Interface(self, self.edges[0]),
            'bottom_back': pyg.Interface(self, self.edges[1]),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyg.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyg.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length, 0])


class TorsoBackHalfPanel(pyg.Panel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    def __init__(self, name, body, design) -> None:
        """ Front = True, provides the adjustments necessary for the front panel
        """
        super().__init__(name)

        design = design['shirt']
        # account for ease in basic measurements
        m_width = design['width']['v'] * body['bust']
        b_width = m_width

        # sizes 
        body_width = body['back_width'] / 2
        frac = body_width / body['bust'] 
        self.width = frac * m_width
        b_width = frac * b_width

        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        length = design['length']['v'] * body['waist_line']

        self.edges = pyg.esf.from_verts(
            [0, 0], 
            [-b_width, 0], 
            [-self.width, length], 
            [0, length + shoulder_incl], 
            loop=True
        )

        # Interfaces
        self.interfaces = {
            'outside':  pyg.Interface(self, self.edges[1]),   
            'inside': pyg.Interface(self, self.edges[-1]),
            'shoulder': pyg.Interface(self, self.edges[-2]),
            'bottom': pyg.Interface(self, self.edges[0]),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyg.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyg.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length, 0])

