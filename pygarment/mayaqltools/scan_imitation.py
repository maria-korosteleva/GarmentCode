"""
    Maya script for removing faces from 3D garement model that are not visible from the outside cameras
    The goal is to imitate scanning artifacts that result in missing geometry
    * Maya 2022+
"""

from maya import OpenMaya
from maya import cmds
import numpy as np
from datetime import datetime

# My modules 
from mayaqltools import utils


def _sample_on_sphere(rad):
    """Uniformly sample a point on a sphere with radious rad. Return as Maya-compatible floating-point vector"""
    # Using method of (Muller 1959, Marsaglia 1972)
    # see the last one here https://mathworld.wolfram.com/SpherePointPicking.html

    uni_array = np.random.normal(size=3)

    uni_array = uni_array / np.linalg.norm(uni_array) * rad

    return OpenMaya.MFloatVector(uni_array[0], uni_array[1], uni_array[2])


def _camera_surface(target, obstacles=[], vertical_scaling_factor=1.5, ground_scaling_factor=1.2):
    """Generate a (3D scanning) camera surface around provided scene"""

    # basically, draw a bounding box around the target
    bbox = np.array(cmds.exactWorldBoundingBox(obstacles + [target]))  # [xmin, ymin, zmin, xmax, ymax, zmax]
    
    top = bbox[3:]
    bottom = bbox[:3]
    center = (top + bottom) / 2
    dims = top - bottom
    dims = [max(dims[0], dims[2]) * ground_scaling_factor, dims[1] * vertical_scaling_factor]

    cube = cmds.polyCube(height=dims[1], depth=dims[0], width=dims[0], name='camera_surface')
    
    # align with center
    cmds.move(center[0], center[1], center[2], cube, absolute=True)

    # remove bottom face -- as if no cameras there
    # adding '.f[1]' would also remove the ceiling
    cmds.polyDelFacet( cube[0] + '.f[3]')    # we know exact structure of default polyCube in Maya2018 & Maya2020

    return cube[0], np.max(dims)


def remove_invisible(target, obstacles=[], num_rays=30, visibile_rays=4):
    """Update target 3D mesh: remove faces that are not visible from camera_surface
        * due to self-occlusion or occlusion by an obstacle
        * Camera surface is generated aroung the target as a small "room" with empty floor and ceiling

        In my context, target is usually a garment mesh, and obstacle is a body surface
        Noise control: 
        * num_rays -- number of random rays to emit from each face -- the less rays, the more noisy the output is
        * visibile_rays -- number of rays to hit camera surface without obstacles to consider the face to be visible
        BUT at least one ray is always required to consider face as visible!
    """
    # Follows the idea of self_intersect_3D() checks used in simulation pipeline
    print('Performing scanning imitation on {} with obstacles {}'.format(target, obstacles))
    
    # generate apropriate camera surface
    camera_surface_obj, ray_dist = _camera_surface(target, obstacles)

    start_time = datetime.now()

    # get mesh objects as OpenMaya object
    target_mesh, target_dag = utils.get_mesh_dag(target)
    camera_surface_mesh, _ = utils.get_mesh_dag(camera_surface_obj)
    obstacles_meshes = [utils.get_mesh_dag(name)[0] for name in obstacles]

    # search for intersections
    target_accelerator = target_mesh.autoUniformGridParams()
    cam_surface_accelerator = camera_surface_mesh.autoUniformGridParams()
    obstacles_accs = [mesh.autoUniformGridParams() for mesh in obstacles_meshes]
    to_delete = []

    target_face_iterator = OpenMaya.MItMeshPolygon(target_dag)
    while not target_face_iterator.isDone():  # https://stackoverflow.com/questions/40422082/how-to-find-face-neighbours-in-maya
        # midpoint of the current face -- start of all the rays
        face_mean = OpenMaya.MFloatPoint(target_face_iterator.center(OpenMaya.MSpace.kWorld))
        face_id = target_face_iterator.index()

        visible_count = 0
        visible = False
        # Send rays in all directions from the currect vertex
        for _ in range(num_rays):
            rayDir = _sample_on_sphere(ray_dist)
            # Case when face is visible from camera surface
            if (utils.test_ray_intersect(camera_surface_mesh, face_mean, rayDir, cam_surface_accelerator)  # intesection with camera surface
                    and not any([utils.test_ray_intersect(mesh, face_mean, rayDir, acc,) for mesh, acc in zip(obstacles_meshes, obstacles_accs)])  # intesects any of the obstacles
                    and not utils.test_ray_intersect(target_mesh, face_mean, rayDir, target_accelerator, hit_tol=1e-5)):  # intersects itself
                visible_count += 1
                if visible_count >= visibile_rays:  # enough rays are visible -- no need to test more
                    visible = True

        if not visible:
            to_delete.append(face_id)
        target_face_iterator.next()  # iterate!

    cmds.delete(camera_surface_obj)  # clean-up the scene

    # Remove invisible faces
    delete_strs = [target + '.f[{}]'.format(face_id) for face_id in to_delete]
    if len(delete_strs) > 0:
        cmds.polyDelFacet(tuple(delete_strs))  # as this is the last command to execute, it could be undone with Ctrl-Z once

    passed = datetime.now() - start_time
    print('{}::Removed {} faces after {}. Press Ctrl-Z to undo the changes'.format(target, len(to_delete), passed))

    return len(to_delete), passed.total_seconds()
    

if __name__ == "__main__":
    # Sample script that can be run within Maya for testing purposes
    # Copy the following block to Maya script editor and modify to 
    import maya.cmds as cmds
    import mayaqltools as mymaya
    from importlib import reload
    reload(mymaya)

    body = cmds.ls('*f_smpl*:Mesh')[0]
    garment = cmds.ls('*tee*:Mesh')[0]  # :Mesh
    # cam_surface = cmds.ls('*camera_surface*')[0]

    mymaya.scan_imitation.remove_invisible(garment, [body], 20, 2)
    # cube = mymaya.scan_imitation.camera_surface(garment, [body])
    # print cube