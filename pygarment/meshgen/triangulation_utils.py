"""Helper functions for the triangulation of the panels"""

import numpy as np
import matplotlib.pyplot as plt

# CGAL 2D
import CGAL.CGAL_Kernel
from CGAL.CGAL_Kernel import Point_2
from CGAL.CGAL_Mesh_2 import Mesh_2_Constrained_Delaunay_triangulation_2
from CGAL.CGAL_Mesh_2 import Delaunay_mesh_size_criteria_2
from CGAL import CGAL_Mesh_2
from CGAL.CGAL_Triangulation_2 import Constrained_Delaunay_triangulation_2


class FaceInfo2(object):
    """
    https://github.com/CGAL/cgal-swig-bindings/blob/main/examples/python/polygonal_triangulation.py#L9
    """
    def __init__(self):
        self.nesting_level = -1

    def in_domain(self):
        return (self.nesting_level % 2) != 1

def mark_domains(ct, start_face, index, edge_border, face_info):
    """
    https://github.com/CGAL/cgal-swig-bindings/blob/main/examples/python/polygonal_triangulation.py#L17
    """
    if face_info[start_face].nesting_level != -1:
        return
    queue = [start_face]
    while queue != []:
        fh = queue[0]  # queue.front
        queue = queue[1:]  # queue.pop_front
        if face_info[fh].nesting_level == -1:
            face_info[fh].nesting_level = index
            for i in range(3):
                e = (fh, i)
                n = fh.neighbor(i)
                if face_info[n].nesting_level == -1:
                    if ct.is_constrained(e):
                        edge_border.append(e)
                    else:
                        queue.append(n)

def mark_domain(cdt):
    """Find a mapping that can be tested to see if a face is in a domain

    Explore the set of facets connected with non constrained edges,
    and attribute to each such set a nesting level.

    We start from the facets incident to the infinite vertex, with a
    nesting level of 0. Then we recursively consider the non-explored
    facets incident to constrained edges bounding the former set and
    increase the nesting level by 1.

    Facets in the domain are those with an odd nesting level.

    https://github.com/CGAL/cgal-swig-bindings/blob/main/examples/python/polygonal_triangulation.py#L36
    """
    face_info = {}
    for face in cdt.all_faces():
        face_info[face] = FaceInfo2()
    index = 0
    border = []
    mark_domains(cdt, cdt.infinite_face(), index + 1, border, face_info)
    while border != []:
        e = border[0]  # border.front
        border = border[1:]  # border.pop_front
        n = e[0].neighbor(e[1])
        if face_info[n].nesting_level == -1:
            lvl = face_info[e[0]].nesting_level + 1
            mark_domains(cdt, n, lvl, border, face_info)
    return face_info

def plot_triangulation(cdt,face_info):
    """
    https://github.com/CGAL/cgal-swig-bindings/blob/main/examples/python/polygonal_triangulation.py#L77
    """
    def rescale_plot(ax, scale=1.1):
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        xmid = (xmin + xmax) / 2.0
        ymid = (ymin + ymax) / 2.0
        xran = xmax - xmid
        yran = ymax - ymid
        ax.set_xlim(xmid - xran * scale, xmid + xran * scale)
        ax.set_ylim(ymid - yran * scale, ymid + yran * scale)

    def plot_edge(edge, *args):
        edge_seg = cdt.segment(edge)
        pts = [edge_seg.source(), edge_seg.target()]
        xs = [pts[0].x(), pts[1].x()]
        ys = [pts[0].y(), pts[1].y()]
        plt.plot(xs, ys, *args)

    for edge in cdt.finite_edges():
        if cdt.is_constrained(edge):
            plot_edge(edge, 'r-')
        else:
            if face_info[edge[0]].in_domain():
                plot_edge(edge, 'b-')
    rescale_plot(plt.gca())
    plt.show()

def get_edge_vert_ids(edges):
    """
    This function returns a list of index pairs of edge vertices into their corresponding
    panel.panel_vertices defining the border of the panel.
    Input:
        * edges (list): All edges of a panel
    Output:
        * zipped_array (ndarray): ndarray of start and end indices of edge vertices into panel.vertices defining
        the line segments of the panel edges (e.g. [[0,1],[1,2],[2,3],...,[19,20],[20,0]])
    """
    zipped_array = np.empty((0, 2))
    for edge in edges:
        edge_verts_ids = edge.vertex_range
        rolled_list = np.roll(edge_verts_ids, 1, axis=0)
        zipped_array_edge = np.stack((rolled_list, edge_verts_ids), axis=1)[1:]
        zipped_array = np.concatenate((zipped_array, zipped_array_edge), axis=0)

    return zipped_array.astype(int)

def create_cdt_points(cdt, points):
    """
    This function converts the edge vertices to Point_2 objects (if necessary) and inserts them into cdt
    Input:
        * cdt (Mesh_2_Constrained_Delaunay_triangulation_2)
        * points (list): The edge vertices
    Output:
        * cdt_points (list): Mesh_2_Constrained_Delaunay_triangulation_2_Vertex_handle of the edge vertices
    """
    cdt_points = []
    for p in points:
        if isinstance(p,CGAL.CGAL_Kernel.Point_2):
            v = cdt.insert(p)
        else:
            x,y = p
            v = cdt.insert(Point_2(float(x),float(y)))

        cdt_points.append(v)

    return cdt_points

def cdt_insert_constraints(cdt, cdt_points, edge_verts_ids):
    """
    This function defines a planar straight line graph (PSLG) for cdt which represents the boundary
    of the mesh and acts as a constraint of cdt. The function returns a dict of the newly inserted
    points containing the indices they get replaced by.
    Input:
        * cdt (Mesh_2_Constrained_Delaunay_triangulation_2)
        * cdt_points (list): Mesh_2_Constrained_Delaunay_triangulation_2_Vertex_handle of points
        * edge_verts_ids (ndarray): indices into cdt_points of edge vertices
    Output:
        * new_points (dict): Dict with indices into cdt.finite_vertices() of newly inserted points (between
          cdt_points[s_id] and cdt_points[e_id]) as keys. The values of the dict are the respective s_ids
          which replace the indices of the newly inserted points later.
    """
    init_len = cdt.number_of_vertices()
    new_points = {} #[id into cdt.finite_vertices()] -> [replace by this id into cdt.finite_vertices()]

    for s_id, e_id in edge_verts_ids:
        start = cdt_points[s_id]
        end = cdt_points[e_id]
        cdt.insert_constraint(start, end)

        num_verts = cdt.number_of_vertices()
        if init_len != num_verts:
            new_points[num_verts - 1] = s_id
            init_len = num_verts
            print('triangulation_utils::INFO::Generated extra boundary points for sdt contraints. Postprocessing will be performed')

    return new_points

def get_face_v_ids(cdt, points, new_points, check=False, plot = False):
    """
    This function returns the faces of cdt as a list of ints instead of vertex handles.
    Input:
        * cdt (Mesh_2_Constrained_Delaunay_triangulation_2)
        * faces (list): Mesh_2_Constrained_Delaunay_triangulation_2_Face_handle of faces in domain
        * points (list): Mesh vertices (filtered out newly inserted boundary vertices)
        * new_points (dict): Dict with indices into cdt.finite_vertices() of newly inserted points (if existent)
          as keys. The values of the dict are the indices replacing the indices of the newly inserted points.
        * check (bool): if True checks if coordinates of vertex handle from face vertex equals point coordinates
    Output:
        * f (list): (N x 3) list of vertex indices describing the faces

    Note: We first replace the vertex handle's coordinates of all points by their indices into points / cdt_points
    because face_handle stores the vertex coordinates and not their indices into points -> speeds up creation of f
    """
    face_v_ids = []

    if new_points:
        sorted_faces = []
        new_points_ids = new_points.keys()

    pts = list(cdt.finite_vertices())

    if check:
        len_points = len(points)
        for i, v_h in enumerate(pts):
            first_temp = v_h.point()
            first = [first_temp.x(),first_temp.y()]

            if not new_points or i < len_points:
                second = points[i]

            if (not new_points or i < len_points) and (first[0] != second[0] or first[1] != second[1]):
                raise ValueError("coords of vertex handle from face vertex does not equal point coords")
            v_h.set_point(Point_2(i, 0.0))

    else:
        for i, v_h in enumerate(pts):
            v_h.set_point(Point_2(i, 0.0))

    # Keep faces that are in the domain
    face_info_new = mark_domain(cdt)

    for face in cdt.finite_faces():
        if face_info_new[face].in_domain():
            v0_id = int(face.vertex(0).point().x())
            v1_id = int(face.vertex(1).point().x())
            v2_id = int(face.vertex(2).point().x())

            if new_points:
                v_ids = [v0_id,v1_id,v2_id]
                for j, v_id in enumerate(v_ids):
                    if v_id in new_points_ids:
                        v_ids[j] = new_points[v_id]

                #check if face now is not an edge/point and not already inserted in faces
                if not (v_ids[0] == v_ids[1] or v_ids[1] == v_ids[2] or v_ids[0] == v_ids[2]) \
                        and not (sorted_faces and np.any(np.all(np.array(sorted_faces) == sorted(v_ids), axis=1))):
                    face_v_ids.append(v_ids)
                    sorted_faces.append(sorted(v_ids))
            else:
                face_v_ids.append([v0_id, v1_id, v2_id])

    if plot:
        plot_triangulation(cdt, face_info_new)

    f = np.array(face_v_ids)
    return f

def get_faces_sorted(cdt):
    """
    This function returns the faces of cdt as a list of *sorted* ints instead of vertex handles.
    Input:
        * cdt (Mesh_2_Constrained_Delaunay_triangulation_2)
    Output:
        * f (ndaray):  (N x 3) *sorted* list of vertex indices describing the faces
        * points (list): The vertices of cdt whose coordinates have been converted to floats
    """

    face_v_ids = []

    pts = list(cdt.finite_vertices())
    points = []


    for i, v_h in enumerate(pts):
        points.append([v_h.point().x(),v_h.point().y()])
        v_h.set_point(Point_2(i, 0.0))


    # Keep faces that are in the domain
    face_info_new = mark_domain(cdt)

    for face in cdt.finite_faces():
        if face_info_new[face].in_domain():
            v0_id = int(face.vertex(0).point().x())
            v1_id = int(face.vertex(1).point().x())
            v2_id = int(face.vertex(2).point().x())

            sorted_ids = sorted([v0_id, v1_id, v2_id])

            face_v_ids.append(sorted_ids)

    f = np.array(face_v_ids)
    return f, points

def get_keep_vertices(cdt, len_b):
    """
    This function filters out the newly inserted boundary vertices from cdt after executing the CGAL mesh generation.
    Input:
        * cdt (Mesh_2_Constrained_Delaunay_triangulation_2)
        * len_b (int): Number of edge vertices, i.e., vertices forming the panel boundary
    Output:
        * keep_vertices: vertices of cdt without newly inserted boundary points
    """
    faces, points = get_faces_sorted(cdt)
    edges = np.concatenate([faces[:, :2], faces[:, 1:], faces[:, ::2]])
    unique_edges, counts = np.unique(np.array(edges), axis=0, return_counts=True)
    unique_occurring_edges = unique_edges[counts == 1]
    all_bdry_v_ids = np.unique(unique_occurring_edges.flatten())
    new_bdry_v_ids = all_bdry_v_ids[all_bdry_v_ids >= len_b]

    #remove new_boundary_vertices
    keep_vertices = np.delete(points, new_bdry_v_ids, axis=0)

    return list(keep_vertices)

def is_manifold(face_v_ids: np.ndarray, points: np.ndarray, tol=1e-2):
    """Check if the 2D mesh is manifold -- all face triangles are correct triangles"""

    faces = points[face_v_ids]
    face_side_1 = np.linalg.norm(faces[:, 0] - faces[:, 1], axis=1)
    face_side_2 = np.linalg.norm(faces[:, 1] - faces[:, 2], axis=1)
    face_side_3 = np.linalg.norm(faces[:, 0] - faces[:, 2], axis=1)
    side_lengths = np.stack([face_side_1, face_side_2, face_side_3], axis=-1)

    return np.all(side_lengths.sum(axis=1) > 2 * side_lengths.max(axis=1) + tol)
