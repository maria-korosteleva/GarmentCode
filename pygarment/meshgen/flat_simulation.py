import igl
import numpy as np

import warp as wp

# Custom
from pygarment.meshgen.garment import Cloth
from pygarment.meshgen.sim_config import PathCofig


# NOTE: the methods from the cloth that are used as is: 
# run_frame(self)
# create_graph(self)
# render_usd_frame(self, is_live=False):

# TODO Maybe both cloth classes need a base class? 
# TODO Debug after warp update
# TODO debug after paths refactoring

class ClothFlat(Cloth):
    def __init__(self, 
                 name, config, paths: PathCofig, sim_cloth,
                 caching=False, ):
        self.base_cloth = sim_cloth
        # Update paths with new output tag
        paths.sim_tag += '_FLAT'  
        paths.update_sim_paths()

        super().__init__(name, config, paths, caching=caching)

        # TODO Why is it needed?
        self.max_height = max(self.current_verts[:, 1]) / 2  # Set max height to at least half the biggest init height

    def build_stage(self, config):
        builder = wp.sim.ModelBuilder(gravity=-9.81)
        
        #Load cloth vertices
        cloth_vertices, cloth_faces = self.base_cloth.current_verts, self.base_cloth.f_cloth
        self.v_cloth_init = cloth_vertices
        self.f_cloth = cloth_faces
        self.max_height = -1

        cloth_rot_matrix = wp.mat33(0, 1, 0, 0, 0, 1, 1, 0, 0)
        cloth_rot = wp.quat_from_matrix(cloth_rot_matrix)
        cloth_pos = self.get_cloth_position()

        # FIXME (!) The mesh should use original lengths for springs
        # -- if any stretch occured due to wearing on a person, it should be undone!
        builder.add_cloth_mesh(
            pos=cloth_pos,
            rot=cloth_rot,
            scale=1.0,
            vel=(0.0, 0.0, 0.0),
            vertices=cloth_vertices,
            indices=cloth_faces.flatten(),
            density=config.garment_density,
            edge_ke=config.garment_edge_ke,
            edge_kd=config.garment_edge_kd,
            tri_ke=config.garment_tri_ke,
            tri_ka=config.garment_tri_ka,
            tri_kd=config.garment_tri_kd,
            tri_drag=config.garment_tri_drag,
            tri_lift=config.garment_tri_lift,
            add_springs=True,
            spring_ke=config.spring_ke,
            spring_kd=config.spring_kd,
        )

        self.model = builder.finalize(device = self.device) #data is transferred to warp tensors, object used in simulation


    def update(self, frame):
        with wp.ScopedTimer("simulate", print=False, active=True):
            if self.model.enable_particle_particle_collisions:
                self.model.particle_grid.build(self.state_0.particle_q, self.model.particle_max_radius * 2.0)
            
            # NOTE No conditions on re-creating the graph

            if self.sim_use_graph: #GPU
                wp.capture_launch(self.graph)

            else: #CPU: launch kernels without graph
                self._sim_frame_with_substeps()

            # Update vertices of last frame
            self.last_verts = self.current_verts
            self.current_verts = wp.array.numpy(self.state_0.particle_q)
    
    def get_cloth_position(self):
        init_verts = self.v_cloth_init
        # Calculate the mean of the y-values
        mean_y_value = np.mean(init_verts[:, 1])
        # min z-coordinate
        most_negative_z_index = np.abs(np.min(init_verts[:, 2])) + 1.0

        return (-mean_y_value, most_negative_z_index, 0.0)

    # TODO Use routine from the parent object once it's disentangled
    def save_frame(self, final): #stores only v and f (okay for cache)
        v_Cloth_end = self.current_verts
        f_Cloth = self.f_cloth

        # Save v_Cloth_end as obj file
        if final:   
            pathClothFinal = self.paths.g_sim
        else:  # FIXME REmove
            pathClothFinal = self.final_path + "_FLAT_sim_cached.obj"

        #Save final cloth obj file
        igl.write_triangle_mesh(pathClothFinal, v_Cloth_end, f_Cloth)


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

        # TODO Why this condition is needed? -- add a comment
        if max(curr_verts_arr[:, 1]) < self.max_height and \
                (non_static_len == 0 or (non_static_len < len(curr_verts_arr) * 0.01 * non_static_percent)):
            print('\nStatic with {} non-static vertices out of {}'.format(non_static_len, len(curr_verts_arr)))
            # Store last frame
            return True, non_static_len
        else:
            # print('\nStatic with {} non-static vertices out of {}'.format(non_static_len, len(curr_verts_arr)))
            # print('0.1: ' , str(len(diff_L1[diff_L1 > 0.1])/ len(curr_verts_arr) * 100), '\n')
            # print('max height: ', max(curr_verts_arr[:, 1]))
            # print('init max height: ', self.max_height)
            return False, non_static_len



