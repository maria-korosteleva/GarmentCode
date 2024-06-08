import os.path
from copy import deepcopy
from pathlib import Path
from datetime import datetime
import yaml
import shutil 
import numpy as np
import PySimpleGUI as sg

# Custom 
from assets.garment_programs.meta_garment import MetaGarment
from assets.body_measurments.body_params import BodyParameters
import pypattern as pyp

verbose = False

icon_image_b64 = b'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'


class GUIPattern:
    def __init__(self) -> None:
        self.save_path = Path.cwd() / 'Logs' 
        self.png_path = None
        self.tmp_path = Path.cwd() / 'tmp'
        
        # create paths
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        self.ui_id = None   # ID of current object in the interface
        self.body_bottom = None   # Location of body center in the current png representation of a garment
        self.body_params = None

        self.design_sampler = pyp.params.DesignSampler()

        self.body_file = None
        self.design_file = None
        self.design_params = {}
        self.new_body_file(
            Path.cwd() / 'assets/body_measurments/f_smpl_avg.yaml'
        )
        self.new_design_file(
            Path.cwd() / 'assets/design_params/default.yaml'
        )
        self.sew_pattern = None

    def is_ready(self):
        """Check if the State is correct to load and save garments"""
        return self.body_file is not None and self.design_file is not None

    def new_body_file(self, path):
        self.body_file = path
        self.body_params = BodyParameters(path)
        self.reload_garment()

    def new_design_file(self, path):
        self.design_file = path

        # Update values
        with open(path, 'r') as f:
            des = yaml.safe_load(f)['design']
        # FIXME Updating should allows loading partial design files
        # Need nested updates
        self.design_params.update(des)
        if 'left' in self.design_params and not self.design_params['left']['enable_asym']['v']:
            self.sync_left()

        # Update param sampler
        self.design_sampler.load(path)

        # Reload
        self.reload_garment()

    def set_design_param(self, param_path, new_value, reload=True):
        """Set the new value of design params"""

        dic = self.design_params
        param = param_path[-1]

        # Skip the top levels
        # https://stackoverflow.com/a/37704379
        for key in param_path[:-1]:
            dic = dic.setdefault(key, {})
        
        # Ensure correct typization
        if dic[param]['type'] == 'int':
            new_value = int(new_value)
        elif dic[param]['type'] == 'bool':
            new_value = bool(new_value)
        elif dic[param]['type'] == 'float':
            new_value = float(new_value)
        # Otherwise stays as is
        dic[param]['v'] = new_value

        if 'enable_asym' in param_path and new_value == False:
            self.sync_left()

        if ('left' not in param_path 
                and 'meta' not in param_path 
                and not self.design_params['left']['enable_asym']['v']
                and param_path[0] in self.design_params['left']):
            # Copy the fields to the left side
            dic = self.design_params['left']
            # Skip the top levels
            # https://stackoverflow.com/a/37704379
            for key in param_path[:-1]:
                dic = dic.setdefault(key, {})
            if param in dic:  # Some parameters may not be present
                dic[param]['v'] = new_value

        if reload:
            self.reload_garment()

    def sample_design(self):
        """Random design parameters"""

        while True:
            new_design = self.design_sampler.randomize()
            self.design_params.update(new_design)
            if 'left' in self.design_params and not self.design_params['left']['enable_asym']['v']:
                self.sync_left()
            self.reload_garment()

            if self.sew_pattern.is_self_intersecting():
                # Let the user know
                out = sg.popup_yes_no(
                    'A sampled design is self-intersecting. Generate a new one?', 
                    title='Self-Intersecting',
                    icon=icon_image_b64)

                if out == 'No':
                    break
            else:
                break

    def restore_design(self):
        """Restore design values to match the current loaded file"""
        new_design = self.design_sampler.default()
        self.design_params.update(new_design)
        self.reload_garment()

    def reload_garment(self):
        """Reload sewing pattern with current body and design parameters"""
        if self.is_ready():
            self.sew_pattern = MetaGarment(
                'Configured_design', self.body_params, self.design_params)
            self._view_serialize()

    def sync_left(self):
        """Synchronize left and right design parameters"""

        for k in self.design_params['left']:
            if k != 'enable_asym':
                self.design_params['left'][k] = deepcopy(self.design_params[k])

    def _view_serialize(self):
        """Save a sewing pattern svg/png representation to tmp folder be used
        for display"""

        # Clear up the folder from previous version -- it's not needed any more
        self.clear_tmp()
        pattern = self.sew_pattern.assembly()

        if not len(pattern.panel_order()): 
            # Empty pattern
            self.png_path = ''
            return

        # Save as json file
        folder = pattern.serialize(
            self.tmp_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=False, with_text=False, view_ids=False)
        
        self.body_bottom = np.asarray(pattern.body_bottom_shift)
        self.png_size = pattern.png_size

        # get PNG file!
        root, _, files = next(os.walk(folder))
        for filename in files:
            if 'pattern.png' in filename and '3d' not in filename:
                self.png_path = os.path.join(root, filename)
                break

    def clear_tmp(self, root=False):
        """Clear tmp folder"""
        shutil.rmtree(self.tmp_path)
        if not root:
            self.tmp_path.mkdir(parents=True, exist_ok=True)

    # Current state
    def save(self):
        """Save current garment design to self.save_path """

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

        print(f'Success! {self.sew_pattern.name} saved to {folder}')

