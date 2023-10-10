"""Parameter class wrappers around parameter files allowing definition of computed parameters
"""

import yaml
from pathlib import Path


class BodyParametrizationBase():
    """Base class for body parametrization wrappers that allows definition of 
        dependent parameters
    """

    def __init__(self, param_file='') -> None:
        
        self.params = {}
        self.load(param_file)

    def __getitem__(self, key):
        return self.params[key]
    
    def __iter__(self):
        """
        Return an iterator of dict keys
        """
        return iter(self.params)
    
    # Updates
    def __setitem__(self, key, value):
        self.params[key] = value
        self.eval_dependencies()

    def load(self, param_file):
        """Load new values from file"""
        with open(param_file, 'r') as f:
            dict = yaml.safe_load(f)['body']
        self.params.update(dict)
        self.eval_dependencies()  # Parameters have been updated

    # Processing
    def eval_dependencies(self):
        """Evaluate dependent attributes, e.g. after a new value has been set
        
            Define your dependent parameters in the overload of this function
        """
        pass
        
    # Save
    def save(self, path, name='body_measurements'):
        with open(Path(path) / f'{name}.yaml', 'w') as f:
            yaml.dump(
                {'body': self.params}, 
                f,
                default_flow_style=False
            )