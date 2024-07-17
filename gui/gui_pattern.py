from pathlib import Path
from datetime import datetime
import time
import yaml
import shutil 
import numpy as np

# Custom 
from assets.garment_programs.meta_garment import MetaGarment
from assets.body_measurments.body_params import BodyParameters
import pypattern as pyp

verbose = False

class GUIPattern:
    def __init__(self) -> None:
        self.save_path = Path.cwd() / 'Logs' 
        self.svg_filename = None
        self.tmp_path = Path.cwd() / 'tmp'
        
        # create paths
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        self.body_params = None
        self.design_params = {}
        self.design_sampler = pyp.params.DesignSampler()
        self.sew_pattern = None

        self.body_file = None
        self.design_file = None
        self._load_body_file(
            Path.cwd() / 'assets/body_measurments/f_smpl_avg.yaml'
        )
        self._load_design_file(
            Path.cwd() / 'assets/design_params/default.yaml'
        )

        self.is_self_intersecting = False
        
        self.reload_garment()

    def _load_body_file(self, path):
        self.body_file = path
        self.body_params = BodyParameters(path)

    def _load_design_file(self, path):
        self.design_file = path

        # Create values
        with open(path, 'r') as f:
            des = yaml.safe_load(f)['design']

        self.design_params.update(des)
        if 'left' in self.design_params and not self.design_params['left']['enable_asym']['v']:
            self.sync_left()

        # Update param sampler
        self.design_sampler.load(path)

    def set_new_design(self, design):
        self._nested_sync(design, self.design_params)

    def set_new_body_params(self, body_params):
        self.body_params.load_from_dict(body_params)

    def sample_design(self, reload=True):
        """Random design parameters"""

        new_design = self.design_sampler.randomize()
        # NOTE: re-assign the values instead up overwriting them
        self._nested_sync(new_design, self.design_params)


        if 'left' in self.design_params and not self.design_params['left']['enable_asym']['v']:
            self.sync_left()

        if reload:
            self.reload_garment()

    def restore_design(self, reload=True):
        """Restore design values to match the current loaded file"""
        new_design = self.design_sampler.default()
        # re-assign the values instead up overwriting them
        self._nested_sync(new_design, self.design_params)
        
        if reload:
            self.reload_garment()

    def reload_garment(self):
        """Reload sewing pattern with current body and design parameters
        
            NOTE: loading a pattern might be lagging, execute only when needed!
        """
        self.sew_pattern = MetaGarment(
            'Configured_design', self.body_params, self.design_params)
        self.is_self_intersecting = self.sew_pattern.is_self_intersecting()
        self._view_serialize()

    @staticmethod
    def _nested_sync(s_from, s_to):
        if 'v' in s_to:
            s_to['v'] = s_from['v']
        else:
            for key in s_to:
                if key in s_from:
                    GUIPattern._nested_sync(s_from[key], s_to[key])

    def sync_left(self, with_check=False):
        """Synchronize left and right design parameters"""
        # Check if needed in the first place
        if with_check and self.design_params['left']['enable_asym']['v']:
            # Asymmetry enabled, the params should not syncronise 
            return  
        for k in self.design_params['left']:
            if k != 'enable_asym':
                # Use proper value assignment instead of deepcopy
                self._nested_sync(self.design_params[k], self.design_params['left'][k])

    def _view_serialize(self):
        """Save a sewing pattern svg representation to tmp folder be used
        for display"""

        # Clear up the folder from previous version -- it's not needed any more
        self.clear_tmp()
        pattern = self.sew_pattern.assembly()

        try:
            self.svg_filename = f'pattern_{time.time()}.svg'
            dwg = pattern.get_svg(self.tmp_path / self.svg_filename, 
                                  with_text=False, 
                                  view_ids=False,
                                  margin=0
            )
            dwg.save()

            self.svg_bbox_size = pattern.svg_bbox_size
            self.svg_bbox = pattern.svg_bbox
        except pyp.EmptyPatternError:
            self.svg_filename = ''
        
    def clear_tmp(self, root=False):
        """Clear tmp folder"""
        shutil.rmtree(self.tmp_path)
        if not root:
            self.tmp_path.mkdir(parents=True, exist_ok=True)

    # Current state
    def is_design_sectioned(self):
        """Check if design parameters are grouped by sections: 
            the top level of design dictionary does not contain actual parameters    
        """
        for param in self.design_params:
            if 'v' in self.design_params[param]:
                return False
        return True

    def is_slow_design(self) -> bool:
        """Check is parameters that result in slow pattern generation are enabled

            E.g. curved armhole evaluation
        """

        # TODO add Hoody!

        # Pants
        if (self.design_params['meta']['bottom']['v'] == 'Pants'):
            return True

        # Upper garment
        is_not_upper = self.design_params['meta']['upper']['v'] is None
        if is_not_upper:
            return False
        
        # Upper + fitted + strapless
        is_asymm = self.design_params['left']['enable_asym']['v']
        is_fitted = 'Fitted' in self.design_params['meta']['upper']['v']
        is_strapless = self.design_params['shirt']['strapless']['v']
        is_asymm_strapless = self.design_params['left']['shirt']['strapless']['v']

        is_strapless = is_fitted and is_strapless
        is_asymm_strapless = is_fitted and is_asymm_strapless

        # Sleeve potential setup
        sleeves = self.design_params['sleeve']        
        is_sleeveless = sleeves['sleeveless']['v']
        is_curve = sleeves['armhole_shape']['v'] == 'ArmholeCurve'
        is_curve = not is_sleeveless and is_curve
        
        is_asym_sleeveless = self.design_params['left']['sleeve']['sleeveless']['v']
        is_asymm_curve = self.design_params['left']['sleeve']['armhole_shape']['v'] == 'ArmholeCurve'
        is_asymm_curve = not is_asym_sleeveless and is_asymm_curve

        if is_asymm:
            right_check = (not is_strapless) and is_curve
            left_check = (not is_asymm_strapless) and is_asymm_curve
            return right_check or left_check
        else:
            return (not is_strapless) and is_curve

    def save(self):
        """Save current garment design to self.save_path """

        # TODO add geomety when available
        pattern = self.sew_pattern.assembly()

        # Save as json file
        folder = pattern.serialize(
            self.save_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=True, with_text=False, view_ids=False, 
            empty_ok=True)

        self.body_params.save(folder)

        with open(Path(folder) / 'design_params.yaml', 'w') as f:
            yaml.dump(
                {'design': self.design_params}, 
                f,
                default_flow_style=False,
                sort_keys=False
            )

        # pack
        archive = shutil.make_archive(
            self.save_path / Path(folder).name, 'zip',
            root_dir=folder
        )

        print(f'Success! {self.sew_pattern.name} saved to {folder}')

        return archive

