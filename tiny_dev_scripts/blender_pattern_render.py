import bpy
import bmesh

def separate_object_by_parts():
    context = bpy.context
    obj = context.edit_object
    me = obj.data
    bpy.ops.mesh.select_all(action='SELECT')

    bm = bmesh.from_edit_mesh(me)

    # old seams
    old_seams = [e for e in bm.edges if e.seam]
    # unmark
    for e in old_seams:
        e.seam = False
        
    # mark seams from uv islands
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.seams_from_islands()
    seams = [e for e in bm.edges if e.seam]

    print('New seams')
    print(len(seams))

    # split on seams
    bmesh.ops.split_edges(bm, edges=seams)

    print('Split successful')

    bpy.ops.mesh.separate(type='LOOSE')

    print('Separation successful')

def mark_edges_to_render():
    for obj in bpy.context.selected_objects:

        # Assuming objects are separated
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        bpy.ops.mesh.region_to_loop()
        
        bpy.ops.mesh.mark_freestyle_edge(clear=False)


# Body and garment scaling

# Pack UVs ?
# Merge vertices ?

# Separate by loose parts??



# Mark US seams as freestyle edge marks 


# Get the shader
    

# Define color list

# Setup render - countour 

# Go over UV shells and colors
    # Copy shader into a new one
    # Setup new color
    # Select all faces in the UV shell
    # assign the shader 
