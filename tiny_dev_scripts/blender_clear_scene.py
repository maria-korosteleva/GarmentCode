
import bpy

def retreive_obj_tag(tag=''):
    return [obj for obj in bpy.context.scene.objects if tag in obj.name]

def retreive_mat_tag(tag=''):
    # https://s-nako.work/2020/08/how-to-get-material-with-python-api-in-blender/
    return [mat for mat in bpy.data.materials if tag in mat.name]

def select_object(obj, edit_mode=False):
    
    # NOTE: Gives errors for no good reason: bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)  # Make visible to enable delete
    obj.select_set(True)
    if edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')

# Garment objects
garment_pieces = retreive_obj_tag('sim') 

print(garment_pieces)
if len(garment_pieces):
    for obj in garment_pieces:
        select_object(obj)
        
        print(obj.name)
        print(bpy.context.selected_objects)
        
        bpy.ops.object.delete()
    

# Materials
all_mat = retreive_mat_tag('ryan')
if len(all_mat) > 1:
    for i in range(1, len(all_mat)):   # DON"T REMOVE THE ONE AT 0!!!!!
        bpy.data.materials.remove(all_mat[i])
        
obj_mat = retreive_mat_tag('OBJ')
for i in range(len(obj_mat)):   # DON"T REMOVE THE ONE AT 0!!!!!
    bpy.data.materials.remove(obj_mat[i])