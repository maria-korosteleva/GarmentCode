import numpy as np

import pygarment as pyg


class BodyParameters(pyg.BodyParametrizationBase):
    """Custom class that defines calculated body parameters"""

    def __init__(self, param_file='') -> None:
        super().__init__(param_file)

    def eval_dependencies(self, key=None):
        super().eval_dependencies(key)

        if key in ['height', 'head_l', 'waist_line', 'hips_line', None]:
            self.params['_waist_level'] = self.params['height'] - self.params['head_l'] - self.params['waist_line']
            self.params['_leg_length'] = self.params['_waist_level'] - self.params['hips_line']
            
        if key in ['shoulder_w', None]:
            # Correct sleeve line location is a little closer to the neck
            # than the true shoulder width
            self.params['_base_sleeve_balance'] = self.params['shoulder_w'] - 2

        # Balance for the bust dart location
        if key in ['bust_line', 'vert_bust_line', None]:
            if 'vert_bust_line' in self.params:
                self.params['_bust_line'] = (1 - 1/3) * self.params['vert_bust_line'] + 1/3 * self.params['bust_line']
            else: 
                self.params['_bust_line'] = self.params['bust_line']
    
        # Half of the slopes for use in garment (smoother fabric distribution)
        if key in ['hip_inclination', None]:
            self.params['_hip_inclination'] = self.params['hip_inclination'] / 2
        if key in ['shoulder_incl', None]:
            self.params['_shoulder_incl'] = self.params['shoulder_incl'] 

        # Add ease to armhole
        if key in ['armscye_depth', None]:
            self.params['_armscye_depth'] = self.params['armscye_depth'] + 2.5
