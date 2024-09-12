from pathlib import Path 
import yaml
from datetime import datetime

from pygarment.data_config import Properties

class PathCofig:
    """Routines for getting paths to various relevant objects with standard names"""
    def __init__(self, 
                 in_element_path, out_path, in_name, out_name=None, 
                 body_name='', samples_name='', default_body=True,
                 smpl_body=False,
                 add_timestamp=False):
        """Specify 
            * in_element_path
            * our_path -- dataset level output path
            * body_name -- specify to indicate use of default bodies 
            * samples_name -- specify to indicate use of body sampling (reading body name from measurments file)
        """

        self._system = Properties('./system.json')  # TODOlOW More stable path?
        self._body_name = body_name
        self._samples_folder_name = samples_name
        self._use_default_body = default_body
        self.use_smpl_seg = smpl_body

        # Tags
        if out_name is None:
            out_name = in_name
        self.in_tag = in_name
        self.out_folder_tag = f'{out_name}_{datetime.now().strftime("%y%m%d-%H-%M-%S")}' if add_timestamp else out_name
        self.sim_tag = out_name 
        self.boxmesh_tag = out_name

        # Base paths
        self.input = Path(in_element_path)
        self.out = out_path
        self.out_el = Path(out_path) / self.out_folder_tag
        self.out_el.mkdir(parents=True, exist_ok=True)
        
        # Individual file paths
        self._update_in_paths()
        self._update_boxmesh_paths()
        self.update_in_copies_paths()
        self.update_sim_paths()
    
    def _update_in_paths(self):

        # Base path
        if not self._samples_folder_name or self._use_default_body:
            self.bodies_path = Path(self._system['bodies_default_path'])   
        else:
            self.bodies_path = Path(self._system['body_samples_path']) / self._samples_folder_name / 'meshes'

        # Body measurements
        if not self._samples_folder_name:
            self.in_body_mes = self.bodies_path / f'{self._body_name}.yaml'
        else:
            self.in_body_mes = self.input / 'body_measurements.yaml'
        
        with open(self.in_body_mes, 'r') as file:
            body_dict = yaml.load(file, Loader=yaml.SafeLoader)
        if 'body_sample' in body_dict['body']:   # Not present in default measurements
            self._body_name = body_dict['body']['body_sample']

        self.in_body_obj = self.bodies_path / f'{self._body_name}.obj'
        self.in_g_spec = self.input / f'{self.in_tag}_specification.json'
        self.body_seg = Path(self._system['bodies_default_path']) / ('ggg_body_segmentation.json' if not self.use_smpl_seg else 'smpl_vert_segmentation.json')
        self.in_design_params = self.input / 'design_params.yaml'

    def _update_boxmesh_paths(self):

        self.g_box_mesh = self.out_el / f'{self.boxmesh_tag}_boxmesh.obj'
        self.g_box_mesh_compressed = self.out_el / f'{self.boxmesh_tag}_boxmesh.ply'
        self.g_mesh_segmentation = self.out_el / f'{self.boxmesh_tag}_sim_segmentation.txt'
        self.g_orig_edge_len = self.out_el / f'{self.boxmesh_tag}_orig_lens.pickle'
        self.g_vert_labels = self.out_el / f'{self.boxmesh_tag}_vertex_labels.yaml'
        self.g_texture_fabric = self.out_el / f'{self.boxmesh_tag}_texture_fabric.png'
        self.g_texture = self.out_el / f'{self.boxmesh_tag}_texture.png'
        self.g_mtl = self.out_el / f'{self.boxmesh_tag}_material.mtl'
        
    def update_in_copies_paths(self):
        self.g_specs = self.out_el / f'{self.in_tag}_specification.json'
        self.element_sim_props = self.out_el / 'sim_props.yaml'
        self.body_mes = self.out_el / f'{self.in_tag}_body_measurements.yaml'
        self.design_params = self.out_el / f'{self.in_tag}_design_params.yaml'
        
    def update_sim_paths(self):
        self.g_sim = self.out_el / f'{self.sim_tag}_sim.obj'
        self.g_sim_glb = self.out_el / f'{self.sim_tag}_sim.glb'
        self.g_sim_compressed = self.out_el / f'{self.sim_tag}_sim.ply'
        self.usd = self.out_el / f'{self.sim_tag}_simulation.usd'


    def render_path(self, camera_name=''):
        
        fname = f'{self.sim_tag}_render_{camera_name}.png' if camera_name else f'{self.sim_tag}_render.png'
        return self.out_el / fname
        

class SimConfig:
    def __init__(self, sim_props):
        # ---- Paths ----
        # Sim props sections
        self.props = sim_props
        sim_props_option = sim_props['options']
        sim_props_material = sim_props['material']

        # Basic setup
        self.sim_fps = 60.0
        self.sim_substeps = 10 #increase?
        self.sim_wo_gravity_percentage = 0
        self.zero_gravity_steps = self.get_sim_props_value(sim_props, 'zero_gravity_steps', 5)
        self.resolution_scale = self.get_sim_props_value(sim_props, 'resolution_scale', 1.0)
        self.ground = self.get_sim_props_value(sim_props, 'ground', True)

        # Stopping criteria 
        self.static_threshold = self.get_sim_props_value(sim_props, 'static_threshold', 0.01)
        self.max_sim_steps = self.get_sim_props_value(sim_props, 'max_sim_steps', 1000)
        self.max_frame_time = self.get_sim_props_value(sim_props, 'max_frame_time', None)
        if self.max_frame_time is not None:
            self.max_frame_time = int(self.max_frame_time)
        self.max_sim_time = int(self.get_sim_props_value(sim_props, 'max_sim_time', 25 * 60))
        self.non_static_percent = self.get_sim_props_value(sim_props, 'non_static_percent', 5)
        # Quality filter
        self.max_body_collisions = self.get_sim_props_value(sim_props, 'max_body_collisions', 0)
        self.max_self_collisions = self.get_sim_props_value(sim_props, 'max_self_collisions', 0)

        
        # Self-collision prevention properties
        self.enable_particle_particle_collisions = self.get_sim_props_value(
            sim_props_option,
            'enable_particle_particle_collisions', False)
        self.enable_triangle_particle_collisions = self.get_sim_props_value(
            sim_props_option,
            'enable_triangle_particle_collisions', False)
        self.enable_edge_edge_collisions = self.get_sim_props_value(
            sim_props_option,
            'enable_edge_edge_collisions', False)
        self.enable_body_collision_filters = self.get_sim_props_value(
            sim_props_option, 
            'enable_body_collision_filters', 
            False
        )

        # Attachment constraints
        self.enable_attachment_constraint = self.get_sim_props_value(
            sim_props_option, 
            'enable_attachment_constraint', 
            False
        )
        self.attachment_labels = self.get_sim_props_value(
            sim_props_option, 
            'attachment_label_names', 
            []
        )
        self.attachment_frames = self.get_sim_props_value(
            sim_props_option, 
            'attachment_frames', 
            100
        )
        self.attachment_stiffness = self.get_sim_props_value(
            sim_props_option,
            'attachment_stiffness',
            []
        )
        self.attachment_damping = self.get_sim_props_value(
            sim_props_option,
            'attachment_damping',
            []
        )
        if not self.attachment_frames or not self.attachment_labels:
            self.enable_attachment_constraint = False

        # Global damping properties
        self.global_damping_factor = self.get_sim_props_value(
            sim_props_option,'global_damping_factor', 1.) 
        self.global_damping_effective_velocity = self.get_sim_props_value(
            sim_props_option,
            'global_damping_effective_velocity', 0.0) 
        self.global_max_velocity = self.get_sim_props_value(
            sim_props_option,'global_max_velocity', 50.0)  

        # Cloth global collision resolution (reference drag) options
        self.enable_global_collision_filter = self.get_sim_props_value(
            sim_props_option, 
            'enable_global_collision_filter',
            False
        )
        self.enable_cloth_reference_drag = self.get_sim_props_value(
            sim_props_option,
            'enable_cloth_reference_drag', False)
        self.cloth_reference_margin = self.get_sim_props_value(
            sim_props_option,'cloth_reference_margin', 0.1)
        self.cloth_reference_k = self.get_sim_props_value(
            sim_props_option,'cloth_reference_k', 1.0e7)

        # Body smoothing options
        self.enable_body_smoothing = self.get_sim_props_value(
            sim_props_option,'enable_body_smoothing', True)
        self.smoothing_total_smoothing_factor = self.get_sim_props_value(
            sim_props_option,
            'smoothing_total_smoothing_factor', 1)
        self.smoothing_recover_start_frame = self.get_sim_props_value(
            sim_props_option,
            'smoothing_recover_start_frame', 0)
        self.smoothing_frame_gap_between_steps = self.get_sim_props_value(
            sim_props_option,
            'smoothing_frame_gap_between_steps', 5)
        self.smoothing_num_steps = self.get_sim_props_value(
            sim_props_option, 'smoothing_num_steps', 100)
        self.smoothing_num_steps = max(min(
            self.smoothing_num_steps, self.max_sim_steps - self.smoothing_recover_start_frame),
            0)
        if self.smoothing_num_steps == 0:
            self.enable_body_smoothing = False

        # ----- Fabric material properties ----- 
        # Bending 
        self.garment_edge_ke = self.get_sim_props_value(
            sim_props_material,'garment_edge_ke', 50000.0) #default = 100.0
        self.garment_edge_kd = self.get_sim_props_value(
            sim_props_material,'garment_edge_kd',10.0) #default = 0.0
        
        # Area preservation
        self.garment_tri_ke = self.get_sim_props_value(
            sim_props_material,'garment_tri_ke', 10000.0) #default = 100.0, small number = more elasticity
        self.garment_tri_kd = self.get_sim_props_value(
            sim_props_material,'garment_tri_kd', 1.0) #default = 10.0
        self.garment_tri_ka = self.get_sim_props_value(
            sim_props_material, 'garment_tri_ka', 10000.0)  # default = 100.0
        self.garment_tri_drag = 0.0  # default = 0.0
        self.garment_tri_lift = 0.0 #default = 0.0

        # Thickness
        self.garment_density = self.get_sim_props_value(
            sim_props_material,'fabric_density', 1.0)  
        self.garment_radius = self.get_sim_props_value(
            sim_props_material,'fabric_thickness', 0.1)  

        # Spring properties (Distance constraints)
        self.spring_ke = self.get_sim_props_value(
            sim_props_material,'spring_ke', 50000)
        self.spring_kd = self.get_sim_props_value(
            sim_props_material,'spring_kd', 10.0)

        # Soft contact properties (contact between cloth and body)
        self.soft_contact_margin = 0.2 
        self.soft_contact_ke = 1000.0 
        self.soft_contact_kd = 10.0 
        self.soft_contact_kf = 1000.0 
        self.soft_contact_mu = self.get_sim_props_value(
            sim_props_material, 'fabric_friction', 0.5
        )

        # Body material
        self.body_thickness = self.get_sim_props_value(sim_props_option,'body_collision_thickness', 0.0)
        self.body_friction = self.get_sim_props_value(sim_props_option,'body_friction', 0.5)

        # particle properties  
        # Some default values -- not used in cloth sim
        self.particle_ke = 1.0e3 
        self.particle_kd = 1.0e2 
        self.particle_kf = 100.0  
        self.particle_mu = 0.5 
        self.particle_cohesion = 0.0 
        self.particle_adhesion = 0.0 

        # After the initialization
        self.update_min_steps()

    def update_min_steps(self):
        self.min_sim_steps = 0
        if self.enable_body_smoothing: 
            self.min_sim_steps = self.smoothing_recover_start_frame + self.smoothing_num_steps
        if self.enable_attachment_constraint:
            # NOTE: Adding a small number of frames 
            # to allow clothing movement to restart after attachment is released
            self.min_sim_steps = max(self.min_sim_steps, self.attachment_frames + 5)

    def get_sim_props_value(self, sim_props, name, default_value):
        if name in sim_props:
            return sim_props[name]
        return default_value

