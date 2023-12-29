import numpy as np

import pypattern as pyp


class BodyParameters(pyp.BodyParametrizationBase):
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
        
        # TODO By key (for correct gui)
        # TODO But check correct on file load
        if 'vert_bust_line' in self.params:
            self.params['bust_line'] = (1 - 1/3) * self.params['vert_bust_line'] + 1/3 * self.params['bust_line']
        
        self.params['hip_inclination'] /= 2
        
        diff = np.tan(np.deg2rad(self.params['shoulder_incl'] / 2)) * (
            self.params['shoulder_w'] / 2 - self.params['neck_w'] / 2)
        
        print('Bust ', self.params['bust_line'], 'Back_diff ', diff)  # DEBUG
        
        # DRAFT 
        # self.params['waist_line'] -= diff
        # self.params['waist_over_bust_line'] += diff

        # TODO add ease to the armhole


# TODO: - ami - do we need this function ?
if __name__ == "__main__":

    body_file = './assets/body_measurments/f_smpl_avg.yaml'
    body = BodyParameters(body_file)
    body.save('./Logs')
