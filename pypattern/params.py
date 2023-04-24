"""Parameter class to correctly process body and design parameters, 
    while allowing storing values as yaml files externally
"""

import yaml

# DRAFT this whole thing

class BodyParametrization():
    """Parameter class to correctly process body and design parameters"""

    def __init__(self, param_file='', dep_designs=None) -> None:
        
        self.params = {}
        self.design_parametrization = dep_designs  # TODO List

        self.load_file(param_file)

    def __getitem__(self, key):
        return self.params[key]
    
    # Updates
    # TODO setattr instead? 
    # TODO nested for design?
    def __setitem__(self, key, value):
        self.params[key] = value
        self.eval_dependencies()

    def load_file(self, param_file):
        """Load new values from file"""
        with open(param_file, 'r') as f:
            dict = yaml.safe_load(f)['body']
        self.params.update(dict)

    # Processing
    def eval_dependencies(self):
        """Re-evaluate dependent attributes, e.g. after a new value has been set"""
        try:
            self.params['waist_level'] = self.params['height'] - self.params['head_l'] - self.params['waist_line']
        except BaseException as e: 
            print(f'{self.__class__.__name__}::Warning::{e}')
        # Other stuff?

        if self.design_parametrization is not None:
            self.design_parametrization.update(self)
        
    # Save
    def save_file(self, path, name='body_params'):
        pass



class Parameter():
    """Defines a single parameter"""
    pass

class DesignParametrization():
    """Parameter class to correctly process body and design parameters"""

    def __init__(self, param_file='', external_dep=None) -> None:
        
        self.params = {}
        self.in_parametrization = external_dep

        self.load_file(param_file)

        # TODO Process dependent parameters

    # TODO ALLOW nested call
    def __getitem__(self, key):
        # TODO Return dependent or calcualted values! 
        return self.params[key]
    
    # Updates
    # TODO nested for design?
    def __setitem__(self, key, value):
        self.params[key] = value
        self.eval_dependencies()

    def load_file(self, param_file):
        """Load new values from file"""
        with open(param_file, 'r') as f:
            dict = yaml.safe_load(f)['body']
        self.params.update(dict)

    # Processing
    def eval_dependencies(self, body_parametrization=None):
        """Re-evaluate parameter ranges and values on value updates and body parametrization updates"""
        pass

        
    # Save
    def save_file(self, path, name='design_params'):
        pass



if __name__=='__main__':
    body_file = './assets/body_measurments/f_smpl_avg.yaml'
    design_file = './assets/design_params/base.yaml'

    body = BodyParametrization(body_file)
    design = DesignParametrization(design_file, body)
    body.design_parametrization = design

    body.save_file('./Logs')
    design.save_file('./Logs')