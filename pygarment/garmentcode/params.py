"""Parameter class wrappers around parameter files allowing definition of computed parameters
"""
import yaml
from pathlib import Path
from copy import deepcopy
import random 

from pygarment.garmentcode.utils import nested_get, nested_set, close_enough


class BodyParametrizationBase:
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
        self.eval_dependencies(key)

    def load(self, param_file):
        """Load new values from file"""
        with open(param_file, 'r') as f:
            dict = yaml.safe_load(f)['body']
        self.params.update(dict)
        self.eval_dependencies()  # Parameters have been updated

    def load_from_dict(self, in_dict):
        self.params.update(in_dict)
        self.eval_dependencies()  # Parameters have been updated 

    # Processing
    def eval_dependencies(self, key=None):
        """Evaluate dependent attributes, e.g. after a new value has been set
        
            Define your dependent parameters in the overload of this function

            * key -- the information on what field is being updated
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


class DesignSampler:
    """Base class for design parameters sampling """

    def __init__(self, param_file='') -> None:
        
        self.params = {}
        if param_file:
            self.load(param_file)

    def load(self, param_file):
        """Load new values from file"""
        with open(param_file, 'r') as f:
            dict = yaml.safe_load(f)['design']
        self.params.update(dict)

    def default(self):
        return self.params

    # ---- Randomization of values ----
    def randomize(self):
        """Generate random values for the current design parameters"""

        random_params = deepcopy(self.params)

        # NOTE dealing with the nested dict
        self._randomize_subset(random_params, [])
        
        return random_params

    def _randomize_subset(self, random_params, path):

        subset = nested_get(random_params, path) if path else random_params
        for key in subset:
            if 'v' in subset[key].keys():
                self._randomize_value(random_params, path + [key])
            else:
                self._randomize_subset(random_params, path + [key])

    def _randomize_value(self, random_params, path):
        """ Randomize the value of one parameter
        Path is leading to the leaf of param dict. value. 
        """

        range = nested_get(random_params, path + ['range'])
        p_type = nested_get(random_params, path + ['type'])
        
        # Check Defaults
        try: 
            def_prob = nested_get(random_params, path + ['default_prob'])
        except KeyError as e:   # Default probability not given  -> Sample uniformly
            def_prob = None

        def_value = nested_get(self.params, path + ['v'])
        if self.__use_default(def_prob):
            new_val = def_value
        else:
            if 'select' in p_type or p_type == 'bool' or 'file' in p_type:  # All discrete types
                if p_type == 'select_null' and None not in range:
                    range.append(None)
                # Exclude default
                if def_prob is not None:
                    range.remove(def_value) 
                new_val = random.choice(range)
            elif p_type == 'int':
                new_val = self.__randint_exclude(range, None if def_prob is None else def_value)
            elif p_type == 'float':
                new_val = self.__uniform_exclude(range, None if def_prob is None else def_value)

        nested_set(random_params, path + ['v'], new_val)

    def __use_default(self, probability):
        if probability is None:
            return False
        return random.random() < probability
    
    def __randint_exclude(self, range, exclude):
        rand_v = random.randint(*range)
        if exclude is not None and rand_v == exclude:
            return self.__randint_exclude(range, exclude)
    
        return rand_v
    
    def __uniform_exclude(self, range, exclude):
        rand_v = random.uniform(*range)
        if exclude is not None and close_enough(rand_v, exclude):
            return self.__uniform_exclude(range, exclude)  
        
        return rand_v 