import pypattern as pyp


class BodyParameters(pyp.BodyParametrizationBase):
    """Custom class that defines calculated body parameters"""

    def __init__(self, param_file='') -> None:
        super().__init__(param_file)

    def eval_dependencies(self):
        super().eval_dependencies()

        self.params['waist_level'] = self.params['height'] - self.params['head_l'] - self.params['waist_line']
        self.params['leg_length'] = self.params['waist_level'] - self.params['hips_line']


# TODO: - ami - do we need this function ?
if __name__ == "__main__":

    body_file = './assets/body_measurments/f_smpl_avg.yaml'
    body = BodyParameters(body_file)
    body.save('./Logs')
