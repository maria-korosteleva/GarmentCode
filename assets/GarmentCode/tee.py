""" Basic straight upper garment (T-shirt)
    Note that the code is very similar to Bodice. 
    The copy was creates for the sake of simplicity and (possible) future divergence of designs
"""

from copy import copy
import numpy as np

# Custom
import pypattern as pyp

# other assets
from . import sleeves
from . import collars

class TorsoFrontHalfPanel(pyp.Panel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    def __init__(self, name, body, design) -> None:
        """ Front = True, provides the adjustments necessary for the front panel
        """
        super().__init__(name)

        design = design['shirt']
        # account for ease in basic measurements
        m_width = design['width']['v'] + design['ease']['v']

        # sizes 
        body_width = (body['bust'] - body['back_width']) / 2 
        frac = body_width / body['bust'] 
        self.width = frac * m_width

        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        length = design['length']['v']

        # length in the front panel is adjusted due to shoulder inclanation
        # for the correct sleeve fitting
        fb_diff = (frac - (0.5 - frac)) * body['bust']
        length = length - sh_tan * fb_diff

        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-m_width / 4, 0],   # Extra vertex to connect with other bottoms correctly
            [-self.width, 0], 
            [-self.width, length], 
            [0, length + shoulder_incl], 
            loop=True
        )

        # Interfaces
        self.interfaces = {
            'outside':  pyp.Interface(self, self.edges[2]),   
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom_front': pyp.Interface(self, self.edges[0]),
            'bottom_back': pyp.Interface(self, self.edges[1]),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

        # default placement
        self.translate_by([0, body['height'] - body['head_l'] - length, 0])


class TorsoBackHalfPanel(pyp.Panel):
    """Half of a simple non-fitted upper garment (e.g. T-Shirt)
    
        Fits to the bust size
    """
    def __init__(self, name, body, design) -> None:
        """ Front = True, provides the adjustments necessary for the front panel
        """
        super().__init__(name)

        design = design['shirt']
        # account for ease in basic measurements
        m_width = design['width']['v'] + design['ease']['v']

        # sizes 
        body_width = body['back_width'] / 2
        frac = body_width / body['bust'] 
        self.width = frac * m_width

        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.width
        length = design['length']['v']

        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-self.width, 0], 
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
        self.translate_by([0, body['height'] - body['head_l'] - length, 0])


class TorsoHalf(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # Torso
        self.ftorso = TorsoFrontHalfPanel(f'{name}_ftorso', body, design).translate_by([0, 0, 25])
        self.btorso = TorsoBackHalfPanel(f'{name}_btorso', body, design).translate_by([0, 0, -20])

        # Sleeves
        diff = self.ftorso.width - self.btorso.width

        self.sleeve = sleeves.Sleeve(name, body, design, depth_diff=diff)

        _, f_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_front_shape'].projecting_edges(), 
            self.ftorso.interfaces['shoulder_corner'])
        _, b_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_back_shape'].projecting_edges(), 
            self.btorso.interfaces['shoulder_corner'])

        if design['sleeve']['sleeveless']['v']:  
            # No sleeve component, only the cut remains
            del self.sleeve
        else:
            self.stitching_rules.append((self.sleeve.interfaces['in_front'], f_sleeve_int))
            self.stitching_rules.append((self.sleeve.interfaces['in_back'], b_sleeve_int))

        # Collars
        # Front
        collar_type = getattr(collars, design['collar']['f_collar']['v'])
        f_collar = collar_type("", design['collar']['fc_depth']['v'], design['collar']['width']['v'])
        pyp.ops.cut_corner(f_collar, self.ftorso.interfaces['collar_corner'])
        # Back
        collar_type = getattr(collars, design['collar']['b_collar']['v'])
        b_collar = collar_type("", design['collar']['bc_depth']['v'], design['collar']['width']['v'])
        pyp.ops.cut_corner(b_collar, self.btorso.interfaces['collar_corner'])

        self.stitching_rules.append((self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']))   # sides
        self.stitching_rules.append((self.ftorso.interfaces['shoulder'], self.btorso.interfaces['shoulder']))  # tops

        self.interfaces = {
            'front_in': self.ftorso.interfaces['inside'],
            'back_in': self.btorso.interfaces['inside'],

            'f_bottom': self.ftorso.interfaces['bottom_front'],
            'b_bottom': pyp.Interface.from_multiple(
                self.ftorso.interfaces['bottom_back'], self.btorso.interfaces['bottom'])
        }


class Shirt(pyp.Component):
    """Panel for the front of upper garments with darts to properly fit it to the shape"""

    def __init__(self, body, design) -> None:
        name_with_params = f"{self.__class__.__name__}"
        super().__init__(name_with_params)

        # TODO resolving names..
        self.right = TorsoHalf(f'right', body, design)
        self.left = TorsoHalf(f'left', body, design).mirror()

        self.stitching_rules.append((self.right.interfaces['front_in'], self.left.interfaces['front_in']))
        self.stitching_rules.append((self.right.interfaces['back_in'], self.left.interfaces['back_in']))

        self.interfaces = {   # Bottom connection
            'bottom': pyp.Interface.from_multiple(
                self.right.interfaces['f_bottom'],
                self.left.interfaces['f_bottom'],
                self.left.interfaces['b_bottom'], 
                self.right.interfaces['b_bottom'])
        }