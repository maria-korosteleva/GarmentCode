"""
NOTE: This scripts needs to be run on a scene with full setup:
    * Lights
    * Backdrops
    * Fabric material
    * Body model 
NOTE: creating cloth materials: https://www.youtube.com/watch?v=umrARvXC_MI
"""

import bpy
import bmesh

from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib

def retreive_obj_tag(tag=''):
    return [obj for obj in bpy.context.scene.objects if tag in obj.name]

def retreive_mat_tag(tag=''):
    # https://s-nako.work/2020/08/how-to-get-material-with-python-api-in-blender/
    return [mat for mat in bpy.data.materials if tag in mat.name]

def select_object(obj, edit_mode=False):
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    
    # print(obj.select_get())
    # print(bpy.context)
    
    if edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')

def pack_uvs(obj):
    # correct selection
    select_object(obj, edit_mode=True)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')

    # Pack
    bpy.ops.uv.pack_islands(margin=0.001)

    bpy.ops.object.mode_set(mode='OBJECT')  # restore the mode

def separate_object_by_parts(obj):
    # select the object to focus on
    select_object(obj, edit_mode=True)

    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    # old seams
    old_seams = [e for e in bm.edges if e.seam]
    # unmark
    for e in old_seams:
        e.seam = False
        
    # mark seams from uv islands
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.seams_from_islands()
    seams = [e for e in bm.edges if e.seam]

    # split on seams
    bmesh.ops.split_edges(bm, edges=seams)
    bpy.ops.mesh.separate(type='LOOSE')
    
    print('Separation successful')
    
    bpy.ops.object.mode_set(mode='OBJECT')  # recover the mode
    return retreive_obj_tag(obj.name[:5])   # NOTE Could be source of trouble

def mark_edges_to_render(objects):
    for obj in objects:
        print(obj.name)

        select_object(obj, edit_mode=True)
        
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.region_to_loop()  # boundary of our mesh subsection
        
        bpy.ops.mesh.mark_freestyle_edge(clear=False)
        
        
    bpy.ops.object.mode_set(mode='OBJECT')  # recover the mode    
    bpy.ops.object.select_all(action='DESELECT')
    print('Marking edges successful')

def assign_materials(meshes, base_shader):
    # Define color list
    # TODO Update colors?
    # NOTE: from my Maya setup
    # color_hex = ['8594AB', '9FBBBA', 'FACDA7', 'EDA19D', 'CF8299', '8B6B96', 'A4DE87']   # CRAZY SITUATION  + 0.85 https://www.schemecolor.com/crazy-situation.php
    # color_list = np.empty((len(color_hex), 4))
    # for idx in range(len(color_hex)):
    #     color_list[idx] = np.array([int(color_hex[idx][i:i + 2], 16) for i in (0, 2, 4)] + [255.]) / 255.0
        
    cmap = matplotlib.cm.get_cmap('twilight')   # Using smooth Matplotlib colormaps

    # Go over meshes
    for id, obj in enumerate(meshes):
        
        # Copy shader into a new one
        new_shader = base_shader.copy()
        # Setup new color
        # DRAFT color_id = id % len(color_list)
        # DRAFT color = color_list[color_id] # DRAFT * 0.9 # / factor  # gets darker the more labels there are

        color = np.array(cmap(id / len(meshes)))
        color[:3] *= 0.7  # DEBUG Brightness
        print(f'Using color {color} for {new_shader.name}')

        new_shader.node_tree.nodes["ColorRamp.002"].color_ramp.elements[1].color = color
        # DRAF T(0.0869196, 0.124639, 0.315605, 1)

        # assign the shader 
        # https://blenderartists.org/t/how-do-i-select-a-material/593489
        obj.active_material_index = 0
        obj.active_material = new_shader

def render(path):
    filename = 'blender_render_' + datetime.now().strftime("%y%m%d-%H-%M-%S")
    
    cameras = [ob for ob in bpy.context.scene.objects if ob.type == 'CAMERA']
    print(cameras)

    # Save image
    for cam in cameras:
        bpy.context.scene.camera = cam  #https://tuxpool.blogspot.com/2020/02/how-to-set-active-camera-when-blender.html

        # https://stackoverflow.com/questions/14982836/rendering-and-saving-images-through-blender-python
        bpy.context.scene.render.filepath = str(path / (filename + f'_{cam.name}.png'))
        bpy.ops.render.render(write_still = True)


# TODO Multiple garments?
# Load from garment folder? Then save to the same one?
# NOPE: Mesh processing: add a "Solidify" modifier to give the mesh a tiny bit of thickness, 
# consider a subdivision modifier to boost shading smoothness

# ---- Preparation ---- 
# TODO Load body if not yet
#body_path = r"C:\Users\MariaKo\Documents\Code\Procedural-Garments\assets\Bodies\f_average_A40.obj"

garment_path = r"C:\Users\MariaKo\Documents\Docs\GarmentCode SA23\test_models\Dress_50s_230123-21-52-33_specification_sim.obj"
bpy.ops.import_scene.obj(filepath=garment_path)

garment = retreive_obj_tag('sim')[0]  # NOTE Make sure it uses correct name
garment.scale = (1/100, 1/100, 1/100)
pack_uvs(garment)    # Make sure UVs look nice  # TODO Check if working!!

# Separate by loose parts
garment_parts = separate_object_by_parts(garment)

print(garment_parts)

# Mark US seams as freestyle edge marks 
mark_edges_to_render(garment_parts)

# ---- Colors -----
# Material setup: https://www.youtube.com/watch?v=umrARvXC_MI
mat = retreive_mat_tag('ryan')[0]   # NOTE Make sure it uses correct name
assign_materials(garment_parts, mat)
    
# ----- Rendering -----
# Run render for each camera in the scene
path = Path(r'C:\Users\MariaKo\Documents\Docs\GarmentCode SA23\Blender tries')
render(path)

print('Rendering finished')

# And wait.. =)

# TODO (optionally) Delete body and/or all garment objects
