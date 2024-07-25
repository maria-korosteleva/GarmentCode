import trimesh
from nicegui import ui, app
import numpy as np
from PIL import Image
# NOTE Z is the up direction 

def fix_texture(mesh):
    material = mesh.visual.material.to_pbr()
    material.baseColorFactor = [1., 1., 1., 1.]
    material.doubleSided = True  # color both face sides  
    # NOTE remove transparency -- add white background just in case
    white_back = Image.new('RGBA', material.baseColorTexture.size, color=(255, 255, 255, 255))
    white_back.paste(material.baseColorTexture)
    material.baseColorTexture = white_back.convert('RGB')  

    mesh.visual.material = material

def create_lights(scene:ui.scene, intensity=30.0):
    light_positions = np.array([
        np.array([1.60614, 1.23701, 1.5341,]),
        np.array([1.31844, -2.52238, 1.92831]),
        np.array([-2.80522, 2.34624, 1.2594]),
        np.array([0.160261, 3.52215, 1.81789]),
        np.array([-2.65752, -1.26328, 1.41194])
    ])
    light_colors = [
        '#ffffff',
        '#ffffff',
        '#ffffff',
        '#ffffff',
        '#ffffff'
    ]
    z_dirs = np.arctan2(light_positions[:, 1], light_positions[:, 0])

    # Add lights to the scene
    for i in range(len(light_positions)):
        scene.spot_light(
            color=light_colors[i], intensity=intensity,
            angle=np.pi,
            ).rotate(0., 0., -z_dirs[i]).move(light_positions[i][0], light_positions[i][1], light_positions[i][2])

def create_camera(cam_location, fov, scale=1.):
    camera = ui.scene.perspective_camera(fov=fov)
    camera.x = cam_location[0] * scale
    camera.y = cam_location[1] * scale
    camera.z = cam_location[2] * scale

    # direction
    camera.look_at_x = 0
    camera.look_at_y = 0
    camera.look_at_z = cam_location[2] * scale * 2/3

    return camera

def define_3d_scene(garm_path, body_path):
    y_fov = np.pi / 6. 
    camera_location = [0, -200., 1.25]  
    bg_color='#ffffff'

    camera = create_camera(camera_location, y_fov)
    with ui.scene(
        width=1024, height=800, camera=camera, 
        grid=False, background_color=bg_color
        ) as scene:
        # Lights setup
        create_lights(scene, intensity=80.)
        # NOTE: texture is there, just needs a better setup
        scene.gltf(
            garm_path,  # DRAFT '/geo/shirt_mean_sim.glb'
            ).material(side='double').scale(0.01).rotate(np.pi / 2, 0., 0.)
        scene.stl(
            body_path,  # DRAFT '/body/mean_all.stl'
            ).rotate(np.pi / 2, 0., 0.).material(color='#000000')

obj_file = './output/shirt_mean_240724-21-57-46/shirt_mean_sim.obj'
glb_file = './output/shirt_mean_240724-21-57-46/shirt_mean_sim.glb'
body_obj_file = './assets/bodies/mean_all.obj'
body_glb_file = './assets/bodies/mean_all.glb'
body_stl_file = './assets/bodies/mean_all.stl'

app.add_static_files('/geo', './output/shirt_mean_240724-21-57-46')
app.add_static_files('/body', './assets/bodies')

mesh = trimesh.load_mesh(obj_file)
# DRAFT 
fix_texture(mesh)
mesh.export(glb_file)

# TODO pre-calculate for the common bodies
# NOTE Stl file for correct application of body material
b_mesh: trimesh.Trimesh = trimesh.load_mesh(body_obj_file)

bbox = b_mesh.bounds

# DEBUG
print('bbox', bbox)
b_mesh.vertices = b_mesh.vertices + np.array([0, -bbox[0][1], 0])

print('Fixed?', b_mesh.bounds)
b_mesh.export(body_stl_file)

define_3d_scene('/geo/shirt_mean_sim.glb', '/body/mean_all.stl')

ui.run(reload=False)