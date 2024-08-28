from pathlib import Path
import time
import yaml
import shutil 
import string
import random
import trimesh
from copy import deepcopy
from typing import Optional

# Custom 
from assets.garment_programs.meta_garment import MetaGarment
from assets.bodies.body_params import BodyParameters
import pygarment as pyg
from pygarment.meshgen.boxmeshgen import BoxMesh
from pygarment.meshgen.simulation import run_sim
import pygarment.data_config as data_config
from pygarment.meshgen.sim_config import PathCofig

verbose = False

def _id_generator(size=10, chars=string.ascii_uppercase + string.digits):
        """Generate a random string of a given size, see
        https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
        """
        return ''.join(random.choices(chars, k=size))

class GUIPattern:
    def __init__(self) -> None:
        # Unique id to distiguish tab sessions correctly
        self.id = _id_generator(20)

        # Paths setup
        self.save_path_root = Path.cwd() / 'tmp_gui' / 'downloads'  
        self.tmp_path_root = Path.cwd() / 'tmp_gui' / 'display'
        self.save_path = self.save_path_root / self.id
        self.svg_filename = None
        self.saved_garment_archive = ''
        self.saved_garment_folder = ''
        self.tmp_path = self.tmp_path_root / self.id 
        self.paths_3d = None

        # create paths
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        self.body_params = None
        self.design_params = {}
        self.design_sampler = pyg.DesignSampler()
        self.sew_pattern = None

        self.body_file = None
        self.design_file = None
        self._load_body_file(
            Path.cwd() / 'assets/bodies/mean_all.yaml'
        )
        self.default_body_params = deepcopy(self.body_params)
        self._load_design_file(
            Path.cwd() / 'assets/design_params/default.yaml'
        )

        # Status
        self.is_self_intersecting = False
        self.is_in_3D = False

        self.reload_garment()

    def release(self):
        """Clean up tmp files after the session"""
        self.clear_previous_download()
        shutil.rmtree(self.save_path)
        shutil.rmtree(self.tmp_path)

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

    def svg_path(self):
        return self.tmp_path / self.svg_filename

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

        # Get the flat representation
        pattern = self.sew_pattern.assembly()

        # Clear up the folder from previous version -- it's not needed any more
        self.clear_previous_svg()
        try:
            self.svg_filename = f'pattern_{time.time()}.svg'
            dwg = pattern.get_svg(self.tmp_path / self.svg_filename, 
                                  with_text=False, 
                                  view_ids=False,
                                  flat=False,
                                  margin=0
            )
            dwg.save()

            self.svg_bbox_size = pattern.svg_bbox_size
            self.svg_bbox = pattern.svg_bbox
        except pyg.EmptyPatternError:
            self.svg_filename = ''
    
    # Cleaning
    def clear_previous_svg(self):
        """Clear previous svg display file"""
        if self.svg_filename:
            (self.tmp_path / self.svg_filename).unlink()
            self.svg_filename = ''
    
    def clear_previous_download(self):
        """Clear previous download package display file"""
        if self.saved_garment_folder:
            shutil.rmtree(self.saved_garment_folder)
            self.saved_garment_folder = ''
        if self.saved_garment_archive:
            self.saved_garment_archive.unlink()
            self.saved_garment_archive = ''

    def clear_3d(self):
        if self.paths_3d is not None:
            shutil.rmtree(self.paths_3d.out_el)
            self.paths_3d = None

    # 3D
    def drape_3d(self):
        """Run the draping of the current frame"""

        # Config setup 
        props = data_config.Properties('./assets/Sim_props/mid_bending.yaml')   # TODOLOW Parameter?
        props.set_section_stats('sim', fails={}, sim_time={}, spf={}, fin_frame={}, body_collisions={}, self_collisions={})
        props.set_section_stats('render', render_time={})

        # Force the design to be fitted to mean body shape 
        # TODOLOW Support body shape estimation from measurements

        def_sew_pattern = MetaGarment(
            'Configured_design', self.default_body_params, self.design_params)

        # Save the pattern
        pattern_folder = self.save(False, save_pattern=def_sew_pattern)

        # Paths
        paths = PathCofig(
            in_element_path=pattern_folder, 
            out_path=self.save_path,
            in_name=def_sew_pattern.name,
            out_name=self.sew_pattern.name + '_3D',
            body_name='mean_all',  
            smpl_body=False,   # NOTE: depends on chosen body model
            add_timestamp=False
        )

        # Generate and save garment box mesh (if not existent)
        garment_box_mesh = BoxMesh(paths.in_g_spec, props['sim']['config']['resolution_scale'])
        garment_box_mesh.load()
        garment_box_mesh.serialize(
            paths, store_panels=False, uv_config=props['render']['config']['uv_texture'])

        # TODOLOW Don't print progress to console with so many lines
        run_sim(
            garment_box_mesh.name, 
            props, 
            paths,
            save_v_norms=False,
            store_usd=False,  # NOTE: False for fast simulation!, 
            optimize_storage=False,
            verbose=False
        )

        # Convert to displayable element
        mesh = trimesh.load_mesh(paths.g_sim)

        # enable double-sided material for nice viewing
        pbr_material = mesh.visual.material.to_pbr()
        pbr_material.doubleSided = True
        mesh.visual.material = pbr_material
        # export
        mesh.export(paths.g_sim_glb)

        self.paths_3d = paths
        self.is_in_3D = True

        return paths.out_el, paths.g_sim_glb.name

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

        # Has a hoody
        collar_component = self.design_params['collar']['component']['style']['v']
        has_hoody = collar_component is not None and 'Hood' in collar_component

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
            return (not is_strapless) and is_curve or has_hoody

    def save(self, pack=True, save_pattern: Optional[MetaGarment]=None):
        """Save current garment design to self.save_path """

        # Save current pattern
        if save_pattern is None:
            save_pattern = self.sew_pattern

        pattern = save_pattern.assembly()

        # Save as json file
        self.saved_garment_folder = pattern.serialize(
            self.save_path, 
            to_subfolder=True, 
            with_3d=False, with_text=False, view_ids=False, 
            with_printable=True,
            empty_ok=True
        )

        self.saved_garment_folder = Path(self.saved_garment_folder)
        self.body_params.save(self.saved_garment_folder)

        with open(self.saved_garment_folder / 'design_params.yaml', 'w') as f:
            yaml.dump(
                {'design': self.design_params}, 
                f,
                default_flow_style=False,
                sort_keys=False
            )

        # pack
        if pack: 
            # Only add geometry if design didn't change since last drape
            if not self.is_in_3D:
                self.clear_3d()  # Clean any saved 3D if it's not synced with current design
            self.saved_garment_archive = Path(shutil.make_archive(
                self.save_path / '..' / f'{self.saved_garment_folder.name}_{self.id}', 'zip',
                root_dir=self.save_path
            ))

        print(f'Success! {self.sew_pattern.name} saved to {self.saved_garment_folder}')

        return self.saved_garment_archive if pack else self.saved_garment_folder

