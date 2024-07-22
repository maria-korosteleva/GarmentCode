"""Routines for processing UV coordinated for garments and generating texture maps"""
import numpy as np
import igl
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path

# SECTION UV islands texture creation 
def texture_mesh_islands(
        texture_coords, face_texture_coords, 
        out_texture_image_path: Path, 
        out_fabric_tex_image_path: Path = None, 
        out_mtl_file_path: Path = None, 
        boundary_width=0.3, 
        dpi=1200, 
        background_img_path=None,
        background_resolution=1.,
        uv_padding=3, 
        mat_name='islands_texture'
):
    """
        Returns updated uv coordinates (properly normalized and aligned with the created texture)
    """
    all_uvs, boundary_uv_to_draw = unwarp_UV(texture_coords, face_texture_coords, padding=uv_padding)
        
    uv_list, width, height = normalize_UVs(all_uvs, axis_padding=uv_padding)   # NOTE !! Axis padding should match the uv padding

    # Create image
    create_UV_island_texture(
        boundary_uv_to_draw, width, height,
        texture_image_path=out_texture_image_path,
        boundary_width=boundary_width,
        dpi=dpi,
        preserve_alpha=True
    )

    # Create image with fabric background
    if out_fabric_tex_image_path is not None:
        create_UV_island_texture(
            boundary_uv_to_draw, width, height,
            texture_image_path=out_fabric_tex_image_path,
            boundary_width=boundary_width,
            dpi=dpi,
            background_img_path=background_img_path, 
            background_resolution=background_resolution,
            preserve_alpha=False  
        )

    # Save mtl is requested
    if out_mtl_file_path:
        save_texture_mtl(
            out_mtl_file_path, 
            out_fabric_tex_image_path.name if out_fabric_tex_image_path is not None else out_texture_image_path.name, 
            mat_name=mat_name)

    return uv_list

def _uv_connected_components(face_texture_coords):

    # Find connected components of face and vertex texture coords
    face_components = igl.facet_components(face_texture_coords)
    vert_components = igl.vertex_components(face_texture_coords)
    num_ccs = max(face_components) + 1

    return vert_components, face_components, num_ccs

def unwarp_UV(texture_coords, face_texture_coords, padding=3):
    # Unwrap uvs for each connected component------------------------

    vert_components, face_components, num_ccs = _uv_connected_components(face_texture_coords)

    all_uvs = [] # transform all UVs to update obj file
    boundary_uv_to_draw = [] # only draw the boundary UVs

    translate_Y = 0
    translate_X = 0

    shells_per_row = int(num_ccs ** 0.5)
    column_x_shift = 0

    # Loop through each connected component
    for i in range(num_ccs):
        
        # Get faces and vertices of connected component
        faces_in_cc = np.where(face_components == i)[0]
        face_vts_in_cc = face_texture_coords[faces_in_cc]

        # get all vertices of connected component
        verts_in_cc = np.where(vert_components == i)[0]

        all_vert_pos = texture_coords[verts_in_cc]
        
        # Find boundary loop
        bound_verts = igl.boundary_loop(face_vts_in_cc)
        bound_vert_pos = texture_coords[bound_verts]

        # Shift component by bounding box
        bbox = bound_vert_pos.min(axis=0), bound_vert_pos.max(axis=0)
        bbox_len_Y = (bbox[1][1] - bbox[0][1])
        bbox_len_X = (bbox[1][0] - bbox[0][0])
    
        if (i % shells_per_row == 0):
            # Start new column
            translate_Y = padding
            translate_X += (column_x_shift + padding)
            column_x_shift = 0  # restart BBOX collection

        # Update shift
        column_x_shift = max(bbox_len_X, column_x_shift)

        # translate boundary positions
        verts_translated_bound = [(x + translate_X, y + translate_Y) for x, y in bound_vert_pos]
        boundary_uv_to_draw.append(verts_translated_bound)
        
        # translate all positions
        verts_translated = [(x + translate_X, y + translate_Y) for x, y in all_vert_pos]
        all_uvs.extend(verts_translated)
        
        translate_Y = translate_Y + bbox_len_Y + padding

    return all_uvs, boundary_uv_to_draw  

def normalize_UVs(all_uvs, axis_padding=3):
    # normalize all_uvs
    uv_list_raw = np.array(all_uvs)
    uv_list = uv_list_raw

    norm_x = max(uv_list_raw[:,0]) + axis_padding
    uv_list[:,0] = uv_list_raw[:,0] / norm_x
    norm_y = max(uv_list_raw[:,1]) + axis_padding
    uv_list[:,1] = uv_list_raw[:,1] / norm_y

    return uv_list, norm_x, norm_y

def create_UV_island_texture(
        boundary_uv_to_draw, 
        width, height, 
        texture_image_path, 
        boundary_width=0.3, 
        boundary_color='black',
        dpi=1200,
        color_alpha=0.65,
        background_alpha=0.8,
        background_img_path=None,
        background_resolution=5,
        preserve_alpha=True
    ):
    """Create texture image from the set of UV boundary loops (e.g. sewing pattern panels). 
        It renders the border of the loops and fills them in with color 
        Params: 
            * boundary_uv_to_draw -- 2D list -- sequence of 2D vertices on each of the boundaries. The order is IMPORTANT. The vertices will be connected 
                by boundary edges sequentially
            * width, height -- the dimentions of the UV map  
            * texture_image_path -- filepath to same a texture image to
            * boundary_width -- width of the boundary outline 
            * dpi -- resolution of the output image
    """
    n_components = len(boundary_uv_to_draw)

    # Figure size
    fig, ax = plt.subplots()
    fig.set_size_inches(width / 100, height / 100)  # width & height are usually given in cm

    # Colors
    shift = 0.17
    divisor = max(5, n_components)
    cmap = matplotlib.colormaps['twilight']   # copper cool  spring winter twilight  # Using smooth Matplotlib colormaps
    color_sample = [cmap((1 - shift) * id / divisor) for id in range(divisor)]

    # Background -- garment style
    if background_img_path is not None:
        back_crop_scale = background_resolution
        back_img = plt.imread(background_img_path)
        ax.imshow(
            back_img[:int(width * back_crop_scale), :int(height * back_crop_scale), :], 
            extent=[0, width, 0, height], 
            alpha=background_alpha,
            aspect='equal'
        )

    # Draw the UV island boundaries and fill them up
    for i in range(n_components):
        polygon_x = [vert[0] for vert in boundary_uv_to_draw[i]]
        polygon_x.append(polygon_x[0])  # Loop
        polygon_y = [vert[1] for vert in boundary_uv_to_draw[i]]
        polygon_y.append(polygon_y[0])  # Loop

        color = list(color_sample[i])
        color[-1] = color_alpha   # Alpha - transparency for blending with backround

        plt.fill(polygon_x, polygon_y, 
                 color=color, 
                 edgecolor=boundary_color, linestyle='-', linewidth=boundary_width / 2  # Boundary stylings
        )
        
    ax.set_aspect('equal')

    # Set the axis to be tight
    ax.set_xlim([0, width])
    ax.set_ylim([0, height])

    # Hide the axis
    plt.axis('off')

    # Save image
    plt.savefig(texture_image_path, dpi=dpi, bbox_inches='tight', pad_inches=0, transparent=preserve_alpha)

    # Cleanup
    plt.close()

# !SECTION

# SECTION Saving textures information to files
def save_texture_mtl(mtl_file_path, texture_image_name, mat_name='uv_texture'):
    new_material_lines = [
        f'newmtl {mat_name}\n',
        'Ns 0.000000\n',
        'Ka 1.000000 1.000000 1.000000\n',
        'Ks 0.000000 0.000000 0.000000\n',
        'Ke 0.000000 0.000000 0.000000\n',
        'Ni 1.000000\n',
        'd 1.000000\n',
        'illum 1\n',
        f'map_Kd {texture_image_name}\n'
    ]

    with open(mtl_file_path, 'w') as file:
        file.writelines(new_material_lines)

    return mat_name

def save_obj(
        output_file_path, 
        vertices, faces_with_texture, uv_list, 
        vert_normals=None, mtl_file_name=None, mat_name=None):
    """Save an obj file with a texture information (if provided)"""

    with open(output_file_path, 'w') as f:
        if mtl_file_name is not None:
            f.write(f'mtllib {mtl_file_name}\n')

        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")

        for vt in uv_list:
            f.write(f"vt {vt[0]} {vt[1]}\n")

        if vert_normals is not None:
            for vn in vert_normals:
                f.write(f"vn {vn[0]} {vn[1]} {vn[2]}\n")
            
        f.write('s 1\n')
        if mtl_file_name is not None:
            f.write(f'usemtl {mat_name}\n')

        if vert_normals is not None:
            for v_id0, tex_id0, v_id1, tex_id1, v_id2, tex_id2, in faces_with_texture:
                f.write(f"f {v_id0 + 1}/{tex_id0 + 1}/{v_id0 + 1} "
                        f"{v_id1 + 1}/{tex_id1 + 1}/{v_id1 + 1} "
                        f"{v_id2 + 1}/{tex_id2 + 1}/{v_id2 + 1}\n")
        else:
            for v_id0, tex_id0, v_id1, tex_id1, v_id2, tex_id2, in faces_with_texture :
                f.write(f"f {v_id0 + 1}/{tex_id0 + 1} "
                        f"{v_id1 + 1}/{tex_id1 + 1} "
                        f"{v_id2 + 1}/{tex_id2 + 1}\n")

def add_texture_to_obj(obj_file_path, output_file_path, uv_list, mtl_file_name, mat_name):
    # Update OBJ-----------------------------------------------------

    with open(obj_file_path, 'r') as file:
        lines = file.readlines()

    uv_index = 0
    updated_lines = []
    mtllib_exists = False
    inserted = False

    s_and_usemtl_lines = ['s 1\n', f'usemtl {mat_name}\n']

    for line in lines:
        if line.startswith('vt '):
            # Format the new UV coordinates
            uv = uv_list[uv_index]
            new_uv_line = f'vt {uv[0]:.6f} {uv[1]:.6f}\n'
            updated_lines.append(new_uv_line)
            uv_index += 1
        elif line.startswith('mtllib '):
            # Ensure the mtllib line points to the correct MTL file
            new_mtl_line = f'mtllib {mtl_file_name}\n'
            updated_lines.append(new_mtl_line)
            mtllib_exists = True
        elif line.startswith('f') and not inserted:
            # Insert the s and usemtl lines before the first face line
            updated_lines.extend(s_and_usemtl_lines)
            inserted = True
            updated_lines.append(line)
        else:
            updated_lines.append(line)
            
    # If mtllib line does not exist, add it at the beginning
    if not mtllib_exists:
        updated_lines.insert(0, f'mtllib {mtl_file_name}\n')

    with open(output_file_path, 'w') as file:
        file.writelines(updated_lines)

# !SECTION