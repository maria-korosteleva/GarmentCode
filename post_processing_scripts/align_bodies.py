"""Aling body models s.t. they stand exactly on the plane y=0 and save as a new data"""
import igl
import numpy as np
from pathlib import Path
import trimesh

from pygarment.data_config import Properties

def load_mesh(path):
    v, f = igl.read_triangle_mesh(str(path))
    return v, f.flatten(), f

def get_shift_param(body_vertices):
    v_body_arr = np.array(body_vertices)
    min_y = (min(v_body_arr[:, 1]))
    if min_y < 0:
        return abs(min_y)
    return 0.0

def save_mesh(path, v, f):
    igl.write_triangle_mesh(str(path), v=v, f=f, force_ascii=False)


def process_body(path_in, path_out):

    body_vertices, _, body_faces = load_mesh(path_in)   #  self.paths.in_body_obj)
    shift_y = get_shift_param(body_vertices)  

    # body_vertices = body_vertices * b_scale
    if shift_y:
        body_vertices[:, 1] = body_vertices[:, 1] + shift_y
    
    save_mesh(path_out, body_vertices, body_faces)

if __name__ == "__main__":

    system_paths = Properties('./system.json')
    
    # body_folder_path = Path(system_paths['body_samples_path']) / 'body_shapes_and_measures_2023-12-30'
    # body_objs_path = body_folder_path / 'meshes'
    body_objs_path = Path('./assets/bodies')
    # out_path = body_folder_path / 'meshes_aligned'
    out_path = Path('./assets/bodies_aligned')
    out_path.mkdir(parents=True, exist_ok=True)

    # loop over all meshes
    for file in body_objs_path.iterdir():
        if '.obj' in file.name:
            process_body(file, out_path / file.name)

            print(file.name)

    

