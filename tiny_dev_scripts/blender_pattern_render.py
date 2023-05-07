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

def retreive_obj_tag(tag=''):
    return [obj for obj in bpy.context.scene.objects if tag in obj.name]

def retreive_mat_tag(tag=''):
    # https://s-nako.work/2020/08/how-to-get-material-with-python-api-in-blender/
    return [mat for mat in bpy.data.materials if tag in mat.name]

def select_object(obj, edit_mode=False):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    if edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')

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
    return retreive_obj_tag(obj.name)

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
    # TODO Define color list
    # Go over meshes
    for obj in meshes:
        
        # TODO Copy shader into a new one
        # TODO Setup new color
        # assign the shader 
        # https://blenderartists.org/t/how-do-i-select-a-material/593489
        obj.active_material_index = 0
        obj.active_material = base_shader

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

# TODO overall scene setup
# TODO Multiple garments?
# ---- Preparation ---- 
# TODO Load from garment folder?
# TODO Body and garment scaling
# TODO Mesh processing: add a "Solidify" modifier to give the mesh a tiny bit of thickness, 
# consider a subdivision modifier to boost shading smoothness
garment = retreive_obj_tag('sim')[0]  # single one

# Prepare garment for rendering
# TODO pack UVs for correct material
bpy.ops.uv.pack_islands(margin=0.001)

# Separate by loose parts
garment_parts = separate_object_by_parts(garment)

# Mark US seams as freestyle edge marks 
mark_edges_to_render(garment_parts)

# ---- Colors -----
# TODO Make a nice shader!

mat = retreive_mat_tag('exp')[0]

assign_materials(garment_parts, mat)
    

# ----- Rendering -----
# Run render for each camera in the scene
# TODO To folder?
path = Path(r'C:\Users\MariaKo\Documents\Docs\GarmentCode SA23\Blender tries')
render(path)

print('Rendering finished')

# TODO Wait for render?
# And wait.. =)
