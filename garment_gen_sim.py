import os
from pygarment.meshgen.boxmeshgen import BoxMesh
from pygarment.meshgen.simulation import run_sim

import pygarment.customconfig as customconfig
from pygarment.meshgen.sim_config import PathCofig

# TODO command line args


if __name__ == "__main__":

    # Basic simulation properties
    sim_props = {
        'ground': False,   # TODO The following belong in 'options'
        'resolution_scale':  1.0, 
        'zero_gravity_steps': 10,
        # TODO Remove -- old!
        'self_collision_steps': 0,  # NOTE: put to big number to remove self-collision resolution

        # Stopping criteria
        'max_sim_steps': 1000,   
        'max_frame_time': 15,
        'max_meshgen_time': 20,  # in seconds, affects speed
        'max_sim_time': 30 * 60,
        'static_threshold': 0.03,  # 0.01  #1 #depends on the units used,
        'non_static_percent': 1.5 , 

        # Quality Filter
        'max_body_collisions': 30, 
        'max_self_collisions': 500,   
        
        'optimize_storage': False,  

        'material': {},
        'options': {},
    }
    sim_props['options'] = {
        # Reason is unknown
        'enable_particle_particle_collisions': False,
        'enable_triangle_particle_collisions': True,  # TODO MK: I don't see these being used??
        'enable_edge_edge_collisions': True,
        'enable_body_collision_filters': True,  

        'enable_attachment_constraint': True, 
        'attachment_frames': 400,   
        'attachment_label_names': ['lower_interface', 'right_collar', 'left_collar', 'strapless_top'], 
        'attachment_stiffness': [1000., 1000., 1000., 100000.],  # NOTE: nice with the top hanging over
        'attachment_damping': [10., 1., 1., 0.], 

        'global_damping_factor': 0.25,  # 0.1   
        'global_damping_effective_velocity': 0.0,  
        'global_max_velocity': 25.,  #  20

        'enable_global_collision_filter': True,
        'enable_cloth_reference_drag': True,  # DRAFT  True,  # TODO Filter in drag as well
        'cloth_reference_margin': 0.1,

        'enable_body_smoothing': False,  # True,  # FIXME CUDA errors when running with this script
        'smoothing_total_smoothing_factor': 1.0,
        'smoothing_recover_start_frame': 150,
        'smoothing_num_steps': 100,
        'smoothing_frame_gap_between_steps': 1,

        'body_collision_thickness': 0.25,
        'body_friction': 0.5
    }

    sim_props['material'] = { # MK's experiments
        'garment_tri_ka': 10000.0,  # 100.0,  # NOTE: Not used in XPBD

        'garment_edge_ke': 1.,   # 100., 500.,  # NOTE: Bending
        'garment_tri_ke': 10000., # 100.0,    # NOTE: Not used in XPBD
        'spring_ke': 50000.,   # Testing 1000000.,  #10000.,    # NOTE: Stiffness
    
        'garment_edge_kd': 10.0,  # 0.0,
        'garment_tri_kd': 1.0,  # 10.0,       # NOTE: Not used in XPBD
        'spring_kd': 10.,  # 100.0,

        'fabric_density':  1.,  #  1.0,
        'fabric_thickness': 0.1,
        'fabric_friction': 0.5
    }


    # Basic rendering properties
    render_props = {
        'resolution':[800, 800], #[1080, 1080],
        'sides':['front','back'],
        'front_camera_location': [0, 0.97, 4.15], # if None, evaluated automatically  # NOTE: Evaluated to fit the tallest body in the dataset 
        'uv_texture': {
            'seam_width': 0.5,
            'dpi': 1500,
            'fabric_grain_texture_path': './assets/img/fabric_texture.png',  # Or NONE
            'fabric_grain_resolution': 5,
        }
    }

    props = customconfig.Properties() 
    props.set_section_config('sim', **sim_props)
    props.set_section_stats('sim', fails={}, sim_time={}, spf={}, fin_frame={}, body_collisions={}, self_collisions={})
    props.set_section_config('render', **render_props)
    props.set_section_stats('render', render_time={})
    res = sim_props['resolution_scale']
    garment_name = "shirt_mean"    # "dbg_wb" # "dbg_fit_top_pants_smpl" # "dbg_fit_top_pants"
    
    # "to_waist_levels_circle2" 
    
    # "tex_error_rand_3W491I74TU"

    # "dress_pencil_top_position"   
     # "js_mean_all"  # "shirt_mean"  

    paths = PathCofig(
        in_element_path=os.path.join(os.path.dirname(__file__), 'assets', 'Patterns'),  # TODO Path()
        out_path=os.path.join(os.path.dirname(__file__), 'output'),
        in_name=garment_name,
        body_name='mean_all',    # 'f_smpl_average_A40',  # 
        smpl_body=False,   # NOTE: depends on chosen body model
        add_timestamp=True
    )

    # Generate and save garment box mesh (if not existent)
    print(f"Generate box mesh of {garment_name} with resolution {res}...")
    print('\nGarment load: ', paths.in_g_spec)

    garment_box_mesh = BoxMesh(paths.in_g_spec, sim_props['resolution_scale'])
    garment_box_mesh.load()
    specs_path = garment_box_mesh.serialize(
        paths, store_panels=False, uv_config=render_props['uv_texture'])

    props.serialize(paths.element_sim_props)

    run_sim(
        garment_box_mesh.name, 
        props, 
        paths,
        flat=False,  # TODO Debug flat sim paths integration + warp recent updates 
        save_v_norms=False,
        store_usd=False,  # NOTE: False for fast simulation!, 
        optimize_storage=sim_props['optimize_storage'],
        verbose=False
    )
    
    props.serialize(paths.element_sim_props)
