""" Panels for a straight upper garment (T-shirt)
    Note that the code is very similar to Bodice. 
"""
import numpy as np
import pypattern as pyp

from assets.garment_programs.base_classes import BaseBodicePanel


class TorsoFrontHalfPanel(BaseBodicePanel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    def __init__(self, name, body, design) -> None:
        """ Front = True, provides the adjustments necessary for the front panel
        """
        super().__init__(name, body, design)

        design = design['shirt']

        # width
        m_width = design['width']['v'] * body['bust']
        b_width = design['flare']['v'] * m_width

        # sizes 
        body_width = (body['bust'] - body['back_width']) / 2 
        frac = body_width / body['bust'] 
        self.width = frac * m_width
        b_width = frac * b_width

        sh_tan = np.tan(np.deg2rad(body['shoulder_incl']))
        shoulder_incl = sh_tan * self.width
        length = design['length']['v'] * body['waist_line']

        # length in the front panel is adjusted due to shoulder inclination
        # for the correct sleeve fitting
        fb_diff = (frac - (0.5 - frac)) * body['bust']
        length = length - sh_tan * fb_diff

        self.edges = pyp.EdgeSeqFactory.from_verts(
            [0, 0], 
            [-b_width, 0], 
            [-self.width, length], 
            [0, length + shoulder_incl], 
            loop=True
        )

        # Interfaces
        self.interfaces = {
            'outside':  pyp.Interface(self, self.edges[1]),   
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, self.edges[0]),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length - shoulder_incl, 0])

    def get_width(self, level):
        return super().get_width(level) + self.width - self.body['shoulder_w'] / 2


class TorsoBackHalfPanel(BaseBodicePanel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    def __init__(self, name, body, design) -> None:
        """ Front = True, provides the adjustments necessary for the front panel
        """
        super().__init__(name, body, design)

        design = design['shirt']
        # account for ease in basic measurements
        m_width = design['width']['v'] * body['bust']
        b_width = design['flare']['v'] * m_width

        # sizes 
        body_width = body['back_width'] / 2
        frac = body_width / body['bust'] 
        self.width = frac * m_width
        b_width = frac * b_width

        shoulder_incl = (np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        length = design['length']['v'] * body['waist_line']

        self.edges = pyp.EdgeSeqFactory.from_verts(
            [0, 0], 
            [-b_width, 0], 
            [-self.width, length], 
            [0, length + shoulder_incl], 
            loop=True
        )

        # Interfaces
        self.interfaces = {
            'outside':  pyp.Interface(self, self.edges[1]),   
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, self.edges[0]),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length - shoulder_incl, 0])

    def get_width(self, level):
        return super().get_width(level) + self.width - self.body['shoulder_w'] / 2
