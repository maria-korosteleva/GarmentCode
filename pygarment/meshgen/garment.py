import igl
import json
import pickle
import numpy as np
import yaml

import warp as wp

import warp.sim.render
from warp.sim.utils import implicit_laplacian_smoothing
import warp.collision.panel_assignment as assign
from warp.sim.collide import count_self_intersections, count_body_cloth_intersections
from warp.sim.integrator_xpbd import replace_mesh_points

# Custom
from pygarment.meshgen.sim_config import PathCofig, SimConfig
from pygarment.pattern.core import BasicPattern

class Cloth:
    def __init__(self, 
                 name, config: SimConfig, paths: PathCofig, 
                 caching=False):

        self.caching = caching   # Saves intermediate frames, extra logs, etc.
        self.paths = paths
        self.name = name
        self.config = config

        self.sim_fps = config.sim_fps
        self.sim_substeps = config.sim_substeps
        self.zero_gravity_steps = config.zero_gravity_steps
        self.sim_dt = (1.0 / self.sim_fps) / self.sim_substeps
        self.usd_frame_time = 0.0 
        self.sim_use_graph = wp.get_device().is_cuda
        self.device = wp.get_device() if wp.get_device().is_cuda else 'cpu' 
        self.frame = -1

        self.c_scale = 1.0
        self.b_scale = 100.0
        self.body_path = paths.in_body_obj
        
        # collision resolution options
        self.enable_body_smoothing = config.enable_body_smoothing
        self.enable_cloth_reference_drag = config.enable_cloth_reference_drag

        # Build the stage -- model object, colliders, etc.
        self.build_stage(config)

        # -------- Final model settings ----------
        # NOTE: global_viscous_damping: (damping_factor, min_vel_damp, max_vel) 
        # apply damping when vel > min_vel_damp, and clamp vel below max_vel after damping
        # TODO Remove after refactoring Euler integrator
        self.model.global_viscous_damping = wp.vec3(
            (config.global_damping_factor, config.global_damping_effective_velocity, config.global_max_velocity))
        self.model.particle_max_velocity = config.global_max_velocity
        
        self.model.ground = config.ground  

        self.model.global_collision_filter = config.enable_global_collision_filter
        self.model.cloth_reference_drag = self.enable_cloth_reference_drag
        self.model.cloth_reference_margin = config.cloth_reference_margin
        self.model.cloth_reference_k = config.cloth_reference_k
        self.model.cloth_reference_watertight_whole_shape_index = 0
        self.model.enable_particle_particle_collisions = config.enable_particle_particle_collisions
        self.model.enable_triangle_particle_collisions = config.enable_triangle_particle_collisions
        self.model.enable_edge_edge_collisions = config.enable_edge_edge_collisions
        self.model.attachment_constraint = config.enable_attachment_constraint

        self.model.soft_contact_margin = config.soft_contact_margin
        self.model.soft_contact_ke = config.soft_contact_ke
        self.model.soft_contact_kd = config.soft_contact_kd
        self.model.soft_contact_kf = config.soft_contact_kf
        self.model.soft_contact_mu = config.soft_contact_mu

        self.model.particle_ke = config.particle_ke
        self.model.particle_kd = config.particle_kd
        self.model.particle_kf = config.particle_kf
        self.model.particle_mu = config.particle_mu
        self.model.particle_cohesion = config.particle_cohesion
        self.model.particle_adhesion = config.particle_adhesion

        #self.integrator = wp.sim.SemiImplicitIntegrator() #intialize semi-implicit time-integrator
        self.integrator = wp.sim.XPBDIntegrator() #intialize semi-implicit time-integrator
        self.state_0 = self.model.state() #returns state object for model (holds all *time-varying* data for a model)
        self.state_1 = self.model.state() #i.e. body/particle positions and velocities
        if self.caching:
            self.renderer = wp.sim.render.SimRenderer(self.model, str(paths.usd), scaling=1.0)

        if self.sim_use_graph:
            self.create_graph()

        self.last_verts = None
        self.current_verts = wp.array.numpy(self.state_0.particle_q)

    def build_stage(self, config):

        builder = wp.sim.ModelBuilder(gravity=0.0)
        # --------------- Load body info -----------------
        body_vertices, body_indices, body_faces = self.load_obj(self.paths.in_body_obj)
        body_seg = self.read_json(self.paths.body_seg) 

        body_vertices = body_vertices * self.b_scale
        self.shift_y = self.get_shift_param(body_vertices)

        if self.shift_y:
            body_vertices[:, 1] = body_vertices[:, 1] + self.shift_y

        self.v_body = body_vertices
        self.f_body = body_faces
        self.body_indices = body_indices

        # -------------- Load cloth ------------
        cloth_vertices, cloth_indices, cloth_faces = self.load_obj(self.paths.g_box_mesh)
        cloth_seg_dict = assign.read_segmentation(self.paths.g_mesh_segmentation)
        self.cloth_seg_dict = cloth_seg_dict
        stitching_vertices = cloth_seg_dict["stitch"] if 'stitch' in cloth_seg_dict.keys() else []

        cloth_vertices = cloth_vertices * self.c_scale
        if self.shift_y:
            cloth_vertices[:, 1] = cloth_vertices[:, 1] + self.shift_y
        self.v_cloth_init = cloth_vertices
        self.f_cloth = cloth_faces

        #Load ground truth stitching lengths
        if not self.paths.g_orig_edge_len.exists():
            orig_lens_dict = None
            print("no original length dict found")
        else:
            with open(self.paths.g_orig_edge_len, 'rb') as file:
                orig_lens_dict = pickle.load(file)

        cloth_pos = (0.0, 0.0, 0.0)
        cloth_rot = wp.quat_from_axis_angle(wp.vec3(0.0, 1.0, 0.0), wp.degrees(0.0)) #no rotation, but orientation of cloth in world space

        builder.add_cloth_mesh_sewing_spring(
            pos=cloth_pos,
            rot=cloth_rot,
            scale=1.0,
            vel=(0.0, 0.0, 0.0),
            vertices=cloth_vertices,
            indices=cloth_indices,
            resolution_scale=config.resolution_scale,
            orig_lens=orig_lens_dict,
            stitching_vertices=stitching_vertices,
            density=config.garment_density,
            edge_ke=config.garment_edge_ke,
            edge_kd=config.garment_edge_kd,
            tri_ke=config.garment_tri_ke,
            tri_ka=config.garment_tri_ka,
            tri_kd=config.garment_tri_kd,
            tri_drag=config.garment_tri_drag,
            tri_lift=config.garment_tri_lift,
            radius=config.garment_radius,
            add_springs=True,
            spring_ke=config.spring_ke,
            spring_kd=config.spring_kd,
        )

        # ------------ Add a body -----------      
        if self.enable_body_smoothing:
            # Starts sim from smoothed-out body and slowly restores original details
            smoothing_total_smoothing_factor = config.smoothing_total_smoothing_factor
            smoothing_num_steps = config.smoothing_num_steps
            smoothing_recover_start_frame = config.smoothing_recover_start_frame
            smoothing_frame_gap_between_steps = config.smoothing_frame_gap_between_steps
            smoothing_step_size = smoothing_total_smoothing_factor / smoothing_num_steps
            self.body_smoothing_frames = [smoothing_recover_start_frame + smoothing_frame_gap_between_steps*i for i in range(smoothing_num_steps + 1)]
            self.body_smoothing_vertices_list = []
            self.body_smoothing_vertices_list = implicit_laplacian_smoothing(body_vertices, body_indices.reshape(-1, 3), 
                                                                             step_size=smoothing_step_size, 
                                                                             iters=smoothing_num_steps)
            body_vertices = self.body_smoothing_vertices_list.pop()
            self.body_smoothing_frames.pop()
            self.body_indices = body_indices
            self.body_vertices_device_buffer = wp.array(body_vertices, dtype=wp.vec3, device=self.device)
            self.v_body = body_vertices
        
        self.body_mesh = wp.sim.Mesh(body_vertices, body_indices)
        
        body_pos = wp.vec3(0.0, 0, 0.0)
        body_rot = wp.quat_from_axis_angle(wp.vec3(0.0, 1.0, 0.0), wp.degrees(0.0))


        # Cloth-body segemntation
        cloth_reference_labels, body_parts = assign.panel_assignment(
                        cloth_seg_dict, cloth_vertices, cloth_indices, wp.transform(cloth_pos, cloth_rot), 
                        body_seg, body_vertices, body_indices, wp.transform(body_pos, body_rot), 
                        device=self.device,
                        panel_init_labels=self._load_panel_labels(),
                        strategy='closest', 
                        merge_two_legs=True,
                        smpl_body=self.paths.use_smpl_seg
                        )  
        
        face_filters, particle_filter = [], []
        if config.enable_body_collision_filters:
            v_connectivity = self._build_vert_connectivity(cloth_vertices, cloth_indices)
            # Arm filter for the skirts
            face_filters.append(assign.create_face_filter(
                body_vertices, body_indices, body_seg, ['left_arm', 'right_arm', 'arms'], smpl_body=self.paths.use_smpl_seg))
            particle_filter = assign.assign_face_filter_points(
                cloth_reference_labels, 
                ['left_leg', 'right_leg', 'legs'],
                filter_id=0,
                vert_connectivity=v_connectivity
            )

            # Overall filter that ignored internal geometry
            face_filters.append(assign.create_face_filter(
                body_vertices, body_indices, body_seg, ['face_internal'], smpl_body=self.paths.use_smpl_seg))
            particle_filter = assign.assign_face_filter_points(
                cloth_reference_labels, 
                ['body'],
                filter_id=1,   
                vert_connectivity=v_connectivity,
                current_vertex_filter=particle_filter
            )

        self.body_shape_index = 0   # Body is the first collider object to be added
        builder.add_shape_mesh(
            body=-1,
            mesh=self.body_mesh,
            pos=body_pos,
            rot=body_rot,
            scale=wp.vec3(1.0,1.0,1.0), #performed body scaling above
            thickness=config.body_thickness,  
            mu=config.body_friction,
            face_filters=face_filters if face_filters else [[]],
            model_particle_filter_ids = particle_filter,
        )
        
        # ----- Attachment constraint -------

        if config.enable_attachment_constraint:
            self._add_attachment_labels(builder, config)

        # ----- Global collision resolution error ---- 
        for part in body_parts:
            part_v, part_inds = assign.extract_submesh(body_vertices, body_indices, body_parts[part])
            builder.add_cloth_reference_shape_mesh(
                mesh = wp.sim.Mesh(part_v, part_inds),
                name = part,
                pos = body_pos,
                rot = body_rot,
                scale = (1.0,1.0,1.0) #performed body scaling above
            )
        # NOTE: has a side-effect of filling up model.particle_reference_label array 
        self.body_parts_names2index = builder.add_cloth_reference_labels(
            cloth_reference_labels, 
            [   # NOTE: Not adding drag between legs and the body as it's useless and contradicts attachment
                ['left_arm', 'body'], 
                ['right_arm', 'body'], 
                ['left_leg', 'right_leg'],
                ['left_arm', 'left_leg'], 
                ['right_arm', 'left_leg'], 
                ['left_arm', 'right_leg'], 
                ['right_arm', 'right_leg'], 
                ['left_arm', 'legs'], 
                ['right_arm', 'legs'], 
            ]
        )  

        # ------- Finalize --------------
        self.model: wp.sim.Model = builder.finalize(device = self.device) #data is transferred to warp tensors, object used in simulation

    def _add_attachment_labels(self, builder, config):
        with open(self.paths.in_body_mes, 'r') as file:
            body_dict = yaml.load(file, Loader=yaml.SafeLoader)['body']
        with open(self.paths.g_vert_labels, 'r') as f:
            vertex_labels = yaml.load(f, Loader=yaml.SafeLoader)
        
        lables_present = False
        for i, attach_label in enumerate(config.attachment_labels):     
            if attach_label in vertex_labels.keys() and len(vertex_labels[attach_label]) > 0:
                constaint_verts = vertex_labels[attach_label]
                if attach_label == 'lower_interface':
                    lables_present = True
                    if '_waist_level' in body_dict:
                        waist_level = body_dict['_waist_level']
                    else:
                        waist_level = body_dict['height'] - body_dict['head_l'] - body_dict['waist_line']
                    builder.add_attachment(
                        constaint_verts, 
                        wp.vec3(0, waist_level, 0),
                        wp.vec3(0., 1., 0.),    # Vertical attachment
                        stiffness = config.attachment_stiffness[i],
                        damping = config.attachment_damping[i]
                    )
                elif attach_label == 'right_collar':
                    lables_present = True
                    
                    neck_w = body_dict['neck_w'] - 2
                    builder.add_attachment(
                        constaint_verts, 
                        wp.vec3(-neck_w / 2, 0, 0),   
                        wp.vec3(1., 0., 0.),    # Horizontal attachment
                        stiffness = config.attachment_stiffness[i],
                        damping = config.attachment_damping[i]
                    )
                elif attach_label == 'left_collar':
                    lables_present = True
                    
                    neck_w = body_dict['neck_w'] - 2
                    builder.add_attachment(
                        constaint_verts, 
                        wp.vec3(neck_w / 2, 0, 0),   
                        wp.vec3(-1., 0., 0.),    # Horizontal attachment
                        stiffness = config.attachment_stiffness[i],
                        damping = config.attachment_damping[i]
                    )
                elif attach_label == 'strapless_top':
                    lables_present = True

                    # Attach under arm 
                    level = body_dict['height'] - body_dict['head_l'] - body_dict['armscye_depth']
                    builder.add_attachment(
                        constaint_verts, 
                        wp.vec3(0, level, 0),  
                        wp.vec3(0., 1., 0.),    # Vertical attachment
                        stiffness = config.attachment_stiffness[i],
                        damping = config.attachment_damping[i]
                    )
                else:
                    print(f'{self.name}::WARNING::Requested attachment label {attach_label} '
                          'is not supported. Skipped')
                    continue
                    
                print(f'Using attachment for {attach_label} with {len(constaint_verts)} vertices')

        if not lables_present:
            # Loaded garment is not labeled -- update config
            config.enable_attachment_constraint = False
            config.update_min_steps()
            print(f'{self.name}::WARNING::Requested attachment labels {config.attachment_labels} '
                  'are not present. Attachment is turned off'
                )

    def _load_panel_labels(self):
        pattern = BasicPattern(self.paths.g_specs)

        labels = {}
        for name, panel in pattern.pattern['panels'].items():
            labels[name] = panel['label'] if 'label' in panel else ''

        return labels     

    def _sim_frame_with_substeps(self):
        """Basic scheme for simulating a frame update"""
        
        wp.sim.collide(self.model, self.state_0, self.sim_dt * self.sim_substeps)  # Generates contact points for the particles and rigid bodies
        # in the model, to be used in the contact dynamics kernel of the integrator
        # launches kernels

        for s in range(self.sim_substeps):
            self.state_0.clear_forces()  # set particle and body forces to 0s
            self.integrator.simulate(self.model, self.state_0, self.state_1,
                                     self.sim_dt)  # calculate semi-implicit Euler step
            # launches kernels and calculates new particle (and body) positions and velocities
            # swap states
            (self.state_0, self.state_1) = (self.state_1, self.state_0)  # swap prev, new state

    def create_graph(self):
        # create update graph
        wp.capture_begin()  # Captures all subsequent kernel launches and memory operations on CUDA devices.
        
        self._sim_frame_with_substeps()

        self.graph = wp.capture_end()  # returns a handle to a CUDA graph object that can be launched with :func:`~warp.capture_launch()`
        # do not capture kernel launches anymore

    def update(self, frame):
        with wp.ScopedTimer("simulate", print=False, active=True):
            if self.model.enable_particle_particle_collisions:
                # FIXME: Produces cuda errors when activated together with "enable_cloth_reference_drag"
                # Reason is unknown. Or not?
                self.model.particle_grid.build(self.state_0.particle_q, self.model.particle_max_radius * 2.0)
            if frame == self.zero_gravity_steps:
                self.model.gravity = np.array((0.0, -9.81, 0.0))
                if self.sim_use_graph:
                    self.create_graph()
            if self.enable_body_smoothing and frame in self.body_smoothing_frames:
                self.update_smooth_body_shape()
                if self.sim_use_graph:
                    self.create_graph()
            if (self.model.attachment_constraint 
                    and frame >= self.config.attachment_frames):  
                self.model.attachment_constraint = False
                if self.sim_use_graph:
                    self.create_graph()
            
            if self.sim_use_graph: #GPU
                wp.capture_launch(self.graph)

            else: #CPU: launch kernels without graph
                self._sim_frame_with_substeps()

            # Update vertices of last frame
            self.last_verts = self.current_verts
            # NOTE Makes a copy if particle_q device is not CPU
            self.current_verts = wp.array.numpy(self.state_0.particle_q)  
            
    def update_smooth_body_shape(self):
        body_vertices = self.body_smoothing_vertices_list.pop()
        self.v_body = body_vertices
        wp.copy(self.body_vertices_device_buffer,
                wp.array(body_vertices, dtype=wp.vec3, device='cpu', copy=False))

        # Apply new vertices and refit the sructures
        wp.launch(
            kernel=replace_mesh_points,
            dim = len(body_vertices),
            inputs=[self.body_mesh.mesh.id,
                    self.body_vertices_device_buffer],
            device=self.device
        )
        self.body_mesh.mesh.refit()

        #update render
        if self.caching: 
            self.renderer.render_mesh(
                            f'shape_{self.body_shape_index}',
                            body_vertices,
                            None,
                            is_template=True,
                        )

    def render_usd_frame(self, is_live=False):
        with wp.ScopedTimer("render", print=False, active=True):
            start_time = 0.0 if is_live else self.usd_frame_time

            self.renderer.begin_frame(start_time)
            self.renderer.render(self.state_0)
            self.renderer.end_frame()

        self.usd_frame_time += 1.0 / self.sim_fps
        if not is_live:
            self.renderer.save()

    def run_frame(self):
        self.update(self.frame)

        # NOTE: USD Render
        if self.caching:
            self.render_usd_frame()
    
    def read_json(self, path):
        with open(path, 'r') as f:
            data = json.load(f)
            return data
    
    def load_obj(self, path):
        v, f = igl.read_triangle_mesh(str(path))
        return v, f.flatten(), f

    def get_shift_param(self,body_vertices):
        v_body_arr = np.array(body_vertices)
        min_y = (min(v_body_arr[:, 1]))
        if min_y < 0:
            return abs(min_y)
        return 0.0

    def calc_norm(self, a, b, c):
        """
        This function calculates the norm based on the three points a, b, and c.
        Input:
            * self (BoxMesh object): Instance of BoxMesh class from which the function is called
            * a (ndarray): first point taking part in norm calculation
            * b (ndarray): second point taking part in norm calculation
            * c (ndarray): third point taking part in norm calculation
        Output:
            * n_normalized (bool): norm(a,b,c) with length 1
        """
        # Calculate the vectors AB and AC
        AB = np.array(b - a)
        AC = np.array(c - a)

        # Calculate the cross product of AB and AC
        n = np.cross(AB, AC)
        n_normalized = n / np.linalg.norm(n)

        return n_normalized

    def calc_vertex_norms(self):
        vertex_normals = np.zeros((len(self.v_cloth_init), 4))
        for face in self.f_cloth:
            v0, v1, v2 = np.array(self.current_verts)[face]
            face_norm = list(self.calc_norm(v0, v1, v2))
            temp_update = face_norm + [1]
            vertex_normals[face] += temp_update

        vertex_normals = vertex_normals[:, :3] / (vertex_normals[:, 3][:, np.newaxis])
        return vertex_normals

    def save_frame(self, save_v_norms=False): 
        """Save current garment state as an obj file, 
        re-using all the information from boxmesh 
        except for vertices and vertex normals (e.g. textures and faces)
        """
        
        # NOTE: igl routine is not used here because it cannot write any extra info (e.g. texture coords) into obj

        # stores v, f, vf and vn
        # Save cloth with texture and normals
        if save_v_norms:
            vertex_normals = self.calc_vertex_norms()

        v_cloth_sim = self.current_verts
        # Store simulated cloth mesh
        # Read the boxmesh file
        with open(self.paths.g_box_mesh, 'r') as obj_file:
            lines = obj_file.readlines()

        # Modify the vertex positions and normals, if required
        with open(self.paths.g_sim, 'w') as obj_file:
            v_idx = 0
            vn_idx = 0
            for line in lines:
                if line.startswith('v '):
                    new_vertex = v_cloth_sim[v_idx]
                    obj_file.write(f'v {new_vertex[0]} {new_vertex[1]} {new_vertex[2]}\n')
                    v_idx += 1
                elif line.startswith('vn '):
                    if save_v_norms:
                        new_vertex = vertex_normals[vn_idx]
                        obj_file.write(f'vn {new_vertex[0]} {new_vertex[1]} {new_vertex[2]}\n')
                        vn_idx += 1
                else:
                    obj_file.write(line)

    def is_static(self):
        """
            Checks whether garment is in the static equilibrium
            Compares current state with the last recorded state
        """
        threshold = self.config.static_threshold
        non_static_percent = self.config.non_static_percent

        curr_verts_arr = self.current_verts
        last_verts_arr = self.last_verts

        if self.last_verts is None:  # first iteration
            return False, len(curr_verts_arr)

        # Compare L1 norm per vertex
        # Checking vertices change is the same as checking if velocity is zero
        diff = np.abs(curr_verts_arr - last_verts_arr)
        diff_L1 = np.sum(diff, axis=1)

        non_static_len = len(
            diff_L1[diff_L1 > threshold])  # compare vertex-wise to allow accurate control over outliers

        if non_static_len == 0 or (non_static_len < len(curr_verts_arr) * 0.01 * non_static_percent):
            print('\nStatic with {} non-static vertices out of {}'.format(non_static_len, len(curr_verts_arr)))
            # Store last frame
            return True, non_static_len
        else:
            return False, non_static_len

    def count_self_intersections(self):
        model = self.model

        if model.particle_count and model.spring_count: 
            model.particle_self_intersection_count.zero_()
            wp.launch(
                kernel=count_self_intersections,
                dim=model.spring_count,
                inputs=[
                    model.spring_indices,
                    model.particle_shape.id,
                ],
                outputs=[
                    model.particle_self_intersection_count
                ],
                device=model.device,
            )
            return int(wp.array.numpy(self.model.particle_self_intersection_count)[0])
        else: 
            return 0

    def count_body_intersections(self):
        model = self.model

        if model.particle_count:
            model.body_cloth_intersection_count.zero_()
            wp.launch(
                kernel=count_body_cloth_intersections,
                dim=model.spring_count,
                inputs=[
                    model.spring_indices,
                    model.particle_shape.id,
                    model.shape_geo,
                    self.body_shape_index
                ],
                outputs=[
                    model.body_cloth_intersection_count
                ],
                device=model.device,
            )
            return int(wp.array.numpy(self.model.body_cloth_intersection_count)[0])
        else:
            return 0 
        
    def _build_vert_connectivity(self, vertices, indices):
        vert_connectivity = [[] for _ in range(len(vertices))]

        for face_id in range(int(len(indices) / 3)):
            v1, v2, v3 = indices[face_id*3 + 0], indices[face_id*3 + 1], indices[face_id*3 + 2]
            
            vert_connectivity[v1].append(v2)
            vert_connectivity[v1].append(v3)

            vert_connectivity[v2].append(v1)
            vert_connectivity[v2].append(v3)

            vert_connectivity[v3].append(v1)
            vert_connectivity[v3].append(v2)

        return vert_connectivity
