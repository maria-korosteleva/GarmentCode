"""
    Module contains classes needed to simulate garments from patterns in Maya.
"""
# Basic
from functools import partial
import copy
import errno
import numpy as np
import os
import time
from importlib import reload

# Maya
from maya import cmds
from maya import OpenMaya

# Arnold
import mtoa.utils as mutils
from mtoa.cmds.arnoldRender import arnoldRender
import mtoa.core

# My modules
import pattern.wrappers as wrappers
from mayaqltools import qualothwrapper as qw
from mayaqltools import utils
reload(wrappers)
reload(qw)
reload(utils)

class PatternLoadingError(BaseException):
    """To be rised when a pattern cannot be loaded correctly to 3D"""
    pass

class MayaGarment(wrappers.VisPattern):
    """
    Extends a pattern specification in custom JSON format to work with Maya
        Input:
            * Pattern template in custom JSON format
        * import panel to Maya scene TODO
        * cleaning imported stuff TODO
        * Basic operations on panels in Maya TODO
    """
    def __init__(self, pattern_file, clean_on_die=False):
        super(MayaGarment, self).__init__(pattern_file)
        self.self_clean = clean_on_die

        self.last_verts = None
        self.current_verts = None
        self.loaded_to_maya = False
        self.obstacles = []
        self.shader_group = None
        self.MayaObjects = {}
        self.config = {
            'material': {},
            'body_friction': 0.5, 
            'resolution_scale': 5
        }

    def __del__(self):
        """Remove Maya objects when dying"""
        if self.self_clean:
            self.clean(True)

    # ------ Basic operations ------
    def load(self, obstacles=[], shader_group=None, config={}, parent_group=None):
        """
            Loads current pattern to Maya as simulatable garment.
            If already loaded, cleans previous geometry & reloads
            config should contain info on fabric matereials & body_friction (collider friction) if provided
        """
        if self.is_self_intersecting():
            # supplied pattern with self-intersecting panels -- it's likely to crash Maya
            raise PatternLoadingError('{}::{}::Provided pattern has self-intersecting panels. Nothing is loaded'.format(
                self.__class__.__name__, self.name))
    

        if self.loaded_to_maya:
            # save the latest sim info
            self.fetchSimProps()
        self.clean(True)
        
        # Normal flow produces garbage warnings of parenting from Maya. Solution suggestion didn't work, so I just live with them
        self.load_panels(parent_group)
        self.stitch_panels()
        self.loaded_to_maya = True

        self.setShaderGroup(shader_group)

        self.add_colliders(obstacles)
        self._setSimProps(config)

        # should be done on the mesh after stitching, res adjustment, but before sim & clean-up
        self._eval_vertex_segmentation()  

        # remove the junk after garment was stitched and labeled
        self._clean_mesh()

        print('Garment ' + self.name + ' is loaded to Maya')

    def load_panels(self, parent_group=None):
        """Load panels to Maya as curve collection & geometry objects.
            Groups them by panel and by pattern"""
        # top group
        group_name = cmds.group(em=True, n=self.name)  # emrty at first
        if parent_group is not None:
            group_name = cmds.parent(group_name, parent_group)
        self.MayaObjects['pattern'] = group_name
        
        # Load panels as curves
        self.MayaObjects['panels'] = {}
        for panel_name in self.pattern['panels']:
            panel_maya = self._load_panel(panel_name, group_name)

    def stitch_panels(self):
        """
            Create seams between qualoth panels.
            Assumes that panels are already loadeded (as curves).
            Assumes that after stitching every pattern becomes a single piece of geometry
            Returns
                Qulaoth cloth object name
        """
        self.MayaObjects['stitches'] = []
        for stitch in self.pattern['stitches']:
            stitch_id = qw.qlCreateSeam(
                self._maya_curve_name(stitch[0]), 
                self._maya_curve_name(stitch[1]))
            stitch_id = cmds.parent(stitch_id, self.MayaObjects['pattern'])  # organization
            self.MayaObjects['stitches'].append(stitch_id[0])

        # after stitching, only one cloth\cloth shape object per pattern is left -- move up the hierarechy
        children = cmds.listRelatives(self.MayaObjects['pattern'], ad=True)
        cloths = [obj for obj in children if 'qlCloth' in obj]
        cmds.parent(cloths, self.MayaObjects['pattern'])

    def setShaderGroup(self, shader_group=None):
        """
            Sets material properties for the cloth object created from current panel
        """
        if not self.loaded_to_maya:
            raise RuntimeError(
                'MayaGarmentError::Pattern is not yet loaded. Cannot set shader')

        if shader_group is not None:  # use previous othervise
            self.shader_group = shader_group

        if self.shader_group is not None:
            cmds.sets(self.get_qlcloth_geomentry(), forceElement=self.shader_group)

    def save_mesh(self, folder='', tag='sim'):
        """
            Saves cloth as obj file and its per vertex segmentation to a given folder or 
            to the folder with the pattern if not given.
        """
        if not self.loaded_to_maya:
            print('MayaGarmentWarning::Pattern is not yet loaded. Nothing saved')
            return

        if folder:
            filepath = folder
        else:
            filepath = self.path
        self._save_to_path(filepath, self.name + '_' + tag)

    def sim_caching(self, caching=True):
        """Toggles the caching of simulation steps to garment folder"""
        if caching:
            # create folder
            self.cache_path = os.path.join(self.path, self.name + '_simcache')
            try:
                os.makedirs(self.cache_path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:  # ok if directory exists
                    raise
                pass
        else:
            # disable caching
            self.cache_path = ''            

    def clean(self, delete=False):
        """ Hides/removes the garment from Maya scene 
            NOTE all of the maya ids assosiated with the garment become invalidated, 
            if delete flag is True
        """
        if self.loaded_to_maya:
            # Remove from simulation
            cmds.setAttr(self.get_qlcloth_props_obj() + '.active', 0)

            if delete:
                print('MayaGarment::Deleting {}'.format(self.MayaObjects['pattern']))

                 # Clean solver cache properly
                solver = qw.findSolver()
                if solver:
                    qw.qlReinitSolver(self.get_qlcloth_props_obj(), solver)

                cmds.delete(self.MayaObjects['pattern'])
                qw.deleteSolver()

                self.loaded_to_maya = False
                self.MayaObjects = {}  # clean 
            else:
                cmds.hide(self.MayaObjects['pattern'])                

        # do nothing if not loaded -- already clean =)

    def display_vertex_segmentation(self):
        """
            Color every vertes of the garment according to the panel is belongs to
            (as indicated in self.vertex_labels)
        """
        # group vertices by label (it's faster then coloring one-by-one)
        vertex_select_lists = dict.fromkeys(self.panel_order() + ['stitch', 'Other'])
        for key in vertex_select_lists:
            vertex_select_lists[key] = []

        for vert_idx in range(len(self.current_verts)):
            str_label = self.vertex_labels[vert_idx]
            if str_label not in self.panel_order() and str_label != 'stitch':
                str_label = 'Other'

            vert_addr = '{}.vtx[{}]'.format(self.get_qlcloth_geomentry(), vert_idx)
            vertex_select_lists[str_label].append(vert_addr)

        # Contrasting Panel Coloring for visualization
        # https://www.schemecolor.com/bright-rainbow-colors.php
        color_hex = ['FF0900', 'FF7F00', 'FFEF00', '00F11D', '0079FF', 'A800FF']
        color_list = np.empty((len(color_hex), 3))
        for idx in range(len(color_hex)):
            color_list[idx] = np.array([int(color_hex[idx][i:i + 2], 16) for i in (0, 2, 4)]) / 255.0

        start_time = time.time()
        for label, str_label in enumerate(vertex_select_lists.keys()):
            if len(vertex_select_lists[str_label]) > 0:   # 'Other' may not be present at all
                if str_label == 'Other':  # non-segmented becomes white
                    color = np.ones(3)
                elif str_label == 'stitch':  # stitches are black
                    color = np.zeros(3)
                else: 
                    # color selection with expansion if the list is too small
                    factor, color_id = (label // len(color_list)) + 1, label % len(color_list)
                    color = color_list[color_id] / factor  # gets darker the more labels there are

                # color corresponding vertices
                cmds.select(clear=True)
                cmds.select(vertex_select_lists[str_label])
                cmds.polyColorPerVertex(rgb=color.tolist())

        cmds.select(clear=True)

        cmds.setAttr(self.get_qlcloth_geomentry() + '.displayColors', 1)
        cmds.refresh()

    # ------ Simulation ------
    def add_colliders(self, obstacles=[]):
        """
            Adds given Maya objects as colliders of the garment
        """
        if not self.loaded_to_maya:
            raise RuntimeError(
                'MayaGarmentError::Pattern is not yet loaded. Cannot load colliders')
        if obstacles:  # if not given, use previous ones
            self.obstacles = obstacles

        if 'colliders' not in self.MayaObjects:
            self.MayaObjects['colliders'] = []
        for obj in self.obstacles:
            collider = qw.qlCreateCollider(
                self.get_qlcloth_geomentry(), 
                obj
            )
            # apply current friction settings
            qw.setColliderFriction(collider, self.config['body_friction'])
            # organize object tree
            collider = cmds.parent(collider, self.MayaObjects['pattern'])
            self.MayaObjects['colliders'].append(collider)

    def fetchSimProps(self):
        """Fetch garment material & body friction from Maya settings"""
        if not self.loaded_to_maya:
            raise RuntimeError('MayaGarmentError::Pattern is not yet loaded.')

        self.config['material'] = qw.fetchFabricProps(self.get_qlcloth_props_obj())  
        if 'colliders' in self.MayaObjects and self.MayaObjects['colliders']:
            # assuming all colliders have the same value
            friction = qw.fetchColliderFriction(self.MayaObjects['colliders'][0])  
            if friction:
                self.config['body_friction'] = friction

        self.config['collision_thickness'] = cmds.getAttr(self.get_qlcloth_props_obj() + '.thickness')
        
        # take resolution scale from any of the panels assuming all the same
        self.config['resolution_scale'] = qw.fetchPanelResolution()

        return self.config

    def update_verts_info(self):
        """
            Retrieves current vertex positions from Maya & updates the last state.
            For best performance, should be called on each iteration of simulation
            Assumes the object is already loaded & stitched
        """
        if not self.loaded_to_maya:
            raise RuntimeError(
                'MayaGarmentError::Pattern is not yet loaded. Cannot update verts info')

        # working with meshes http://www.fevrierdorian.com/blog/post/2011/09/27/Quickly-retrieve-vertex-positions-of-a-Maya-mesh-%28English-Translation%29
        cloth_dag = self.get_qlcloth_geom_dag()
        
        mesh = OpenMaya.MFnMesh(cloth_dag)

        vertices = utils.get_vertices_np(mesh)

        self.last_verts = self.current_verts
        self.current_verts = vertices

    def cache_if_enabled(self, frame):
        """If caching is enabled -> saves current geometry to cache folder
            Does nothing otherwise """
        if not self.loaded_to_maya:
            print('MayaGarmentWarning::Pattern is not yet loaded. Nothing cached')
            return

        if hasattr(self, 'cache_path') and self.cache_path:
            self._save_to_path(self.cache_path, self.name + '_{:04d}'.format(frame))

    # ------ Qualoth objects ------
    def get_qlcloth_geomentry(self):
        """
            Find the first Qualoth cloth geometry object belonging to current pattern
        """
        if not self.loaded_to_maya:
            raise RuntimeError('MayaGarmentError::Pattern is not yet loaded.')

        if 'qlClothOut' not in self.MayaObjects:
            children = cmds.listRelatives(self.MayaObjects['pattern'], ad=True)
            cloths = [obj for obj in children 
                      if 'qlCloth' in obj and 'Out' in obj and 'Shape' not in obj]
            self.MayaObjects['qlClothOut'] = cloths[0]

        return self.MayaObjects['qlClothOut']

    def get_qlcloth_props_obj(self):
        """
            Find the first qlCloth object belonging to current pattern
        """
        if not self.loaded_to_maya:
            raise RuntimeError('MayaGarmentError::Pattern is not yet loaded.')

        if 'qlCloth' not in self.MayaObjects:
            children = cmds.listRelatives(self.MayaObjects['pattern'], ad=True)
            cloths = [obj for obj in children 
                      if 'qlCloth' in obj and 'Out' not in obj and 'Shape' in obj]
            self.MayaObjects['qlCloth'] = cloths[0]

        return self.MayaObjects['qlCloth']

    def get_qlcloth_geom_dag(self):
        """
            returns DAG reference to cloth shape object
        """
        if not self.loaded_to_maya:
            raise RuntimeError('MayaGarmentError::Pattern is not yet loaded.')

        if 'shapeDAG' not in self.MayaObjects:
            self.MayaObjects['shapeDAG'] = utils.get_dag(self.get_qlcloth_geomentry())

        return self.MayaObjects['shapeDAG']

    # ------ Geometry Checks ------
    def is_static(self, threshold, allowed_non_static_percent=0):
        """
            Checks wether garment is in the static equilibrium
            Compares current state with the last recorded state
        """
        if not self.loaded_to_maya:
            raise RuntimeError(
                'MayaGarmentError::Pattern is not yet loaded. Cannot check static')
        
        if self.last_verts is None:  # first iteration
            return False
        
        # Compare L1 norm per vertex
        # Checking vertices change is the same as checking if velocity is zero
        diff = np.abs(self.current_verts - self.last_verts)
        diff_L1 = np.sum(diff, axis=1)

        non_static_len = len(diff_L1[diff_L1 > threshold])  # compare vertex-wize to allow accurate control over outliers

        if non_static_len == 0 or non_static_len < len(self.current_verts) * 0.01 * allowed_non_static_percent:  
            print('\nStatic with {} non-static vertices out of {}'.format(non_static_len, len(self.current_verts)))
            return True, non_static_len
        else:
            return False, non_static_len

    def intersect_colliders_3D(self, obstacles=[]):
        """Checks wheter garment intersects given obstacles or its colliders if obstacles are not given
            Returns True if intersections found

            Having intersections may disrupt simulation result although it seems to recover from some of those
        """
        if not self.loaded_to_maya:
            raise RuntimeError('Garment is not yet loaded: cannot check for intersections')

        if not obstacles:
            obstacles = self.obstacles
        
        print('Garment::3D Penetration checks')

        # check intersection with colliders
        for obj in obstacles:
            intersecting = self._intersect_object(obj)

            if intersecting:
                return True
        
        return False

    def self_intersect_3D(self, verbose=False):
        """Checks wheter currently loaded garment geometry intersects itself
            Unline boolOp, check is non-invasive and do not require garment reload or copy.
            
            Having intersections may disrupt simulation result although it seems to recover from some of those
            """
        if not self.loaded_to_maya:
            raise RuntimeError(
                'MayaGarmentError::Pattern is not yet loaded. Cannot check geometry self-intersection')
        
        # It turns out that OpenMaya python reference has nothing to do with reality of passing argument:
        # most of the functions I use below are to be treated as wrappers of c++ API
        # https://help.autodesk.com/view/MAYAUL/2018//ENU/?guid=__cpp_ref_class_m_fn_mesh_html

        mesh, cloth_dag = utils.get_mesh_dag(self.get_qlcloth_geomentry())
        
        vertices = OpenMaya.MPointArray()
        mesh.getPoints(vertices, OpenMaya.MSpace.kWorld)
        
        # use ray intersect with all edges of current mesh & the mesh itself
        num_edges = mesh.numEdges()
        accelerator = mesh.autoUniformGridParams()
        num_hits = 0
        for edge_id in range(num_edges):
            # Vertices that comprise an edge
            vtx1, vtx2 = utils.edge_vert_ids(mesh, edge_id)

            # test intersection
            raySource = OpenMaya.MFloatPoint(vertices[vtx1])
            rayDir = OpenMaya.MFloatVector(vertices[vtx2] - vertices[vtx1])
            hit, hitFaces, hitPoints, _ = utils.test_ray_intersect(mesh, raySource, rayDir, accelerator, return_info=True)
            
            if not hit:
                continue

            # Since edge is on the mesh, we have tons of false hits
            # => check if current edge is adjusent to hit faces: if shares a vertex
            for face_id in range(hitFaces.length()):
                face_verts = OpenMaya.MIntArray()
                mesh.getPolygonVertices(hitFaces[face_id], face_verts)
                face_verts = [face_verts[j] for j in range(face_verts.length())]
                
                if vtx1 not in face_verts and vtx2 not in face_verts:
                    # hit face is not adjacent to the edge => real hit
                    if verbose:
                        print('Hit point: {}, {}, {}'.format(hitPoints[face_id][0], hitPoints[face_id][1], hitPoints[face_id][2]))
                    num_hits += 1
        
        if num_hits == 0:  # no intersections -- no need for threshold check
            print('{} is not self-intersecting'.format(self.name))
            return False

        if ('self_intersect_hit_threshold' in self.config 
                and num_hits > self.config['self_intersect_hit_threshold']
                or num_hits > 0 and 'self_intersect_hit_threshold' not in self.config):  # non-zero hit if no threshold provided
            print('{} is self-intersecting with {} intersect edges -- above threshold {}'.format(
                self.name, num_hits,
                self.config['self_intersect_hit_threshold'] if 'self_intersect_hit_threshold' in self.config else 0))
            return True
        else:
            print('{} is self-intersecting with {} intersect edges -- ignored by threshold {}'.format(
                self.name, num_hits,
                self.config['self_intersect_hit_threshold'] if 'self_intersect_hit_threshold' in self.config else 0))
            # no need to reload -- non-invasive checks 
            return False

    # ------ ~Private -------
    def _load_panel(self, panel_name, pattern_group=None):
        """
            Loads curves contituting given panel to Maya. 
            Goups them per panel
        """
        panel = self.pattern['panels'][panel_name]
        vertices = np.asarray(panel['vertices'])
        self.MayaObjects['panels'][panel_name] = {}
        self.MayaObjects['panels'][panel_name]['edges'] = []

        # top panel group
        panel_group = cmds.group(n=panel_name, em=True)
        if pattern_group is not None:
            panel_group = cmds.parent(panel_group, pattern_group)[0]
        self.MayaObjects['panels'][panel_name]['group'] = panel_group

        # draw edges
        curve_names = []
        for edge in panel['edges']:
            curve_points = self._edge_as_3d_tuple_list(edge, vertices)
            curve = cmds.curve(p=curve_points, d=(len(curve_points) - 1))
            curve_names.append(curve)
            self.MayaObjects['panels'][panel_name]['edges'].append(curve)
        # Group  
        curve_group = cmds.group(curve_names, n=panel_name + '_curves')
        curve_group = cmds.parent(curve_group, panel_group)[0]
        self.MayaObjects['panels'][panel_name]['curve_group'] = curve_group
        # 3D placemement
        self._apply_panel_3d_placement(panel_name)

        # Create geometry
        panel_geom = qw.qlCreatePattern(curve_group)
        # take out the solver node -- created only once per scene, no need to store
        solvers = [obj for obj in panel_geom if 'Solver' in obj]
        panel_geom = list(set(panel_geom) - set(solvers))
        panel_geom = cmds.parent(panel_geom, panel_group)  # organize

        pattern_object = [node for node in panel_geom if 'Pattern' in node]
        
        self.MayaObjects['panels'][panel_name]['qlPattern'] = (
            pattern_object[0] if panel_group in pattern_object[0] else panel_group + '|' + pattern_object[0]
        )

        return panel_group

    def _setSimProps(self, config={}):
        """Pass material properties for cloth & colliders to Qualoth"""
        if not self.loaded_to_maya:
            raise RuntimeError('MayaGarmentError::Pattern is not yet loaded.')

        if config:
            self.config = config

        qw.setFabricProps(
            self.get_qlcloth_props_obj(), 
            self.config['material']
        )

        if 'colliders' in self.MayaObjects:
            for collider in self.MayaObjects['colliders']:
                qw.setColliderFriction(collider, self.config['body_friction'])

        if 'collision_thickness' in self.config:
            # if not provided, use default auto-calculated value
            cmds.setAttr(self.get_qlcloth_props_obj() + '.overrideThickness', 1)
            cmds.setAttr(self.get_qlcloth_props_obj() + '.thickness', self.config['collision_thickness'])

        # update resolution properties
        qw.setPanelsResolution(self.config['resolution_scale'])
    
    def _eval_vertex_segmentation(self):
        """
            Evalute which vertex belongs to which panel
            NOTE: only applicable to the mesh that was JUST loaded and stitched
                -- Before the mesh was cleaned up (because the info from Qualoth is dependent on original topology) 
                -- before the sim started (need planarity checks)
                Hence fuction is only called once on garment load
            NOTE: if garment resolution was changed from Maya tools, 
                the segmentation is not guranteed to be consistent with the change, 
                (reload garment geometry to get correct segmentation)
        """
        if not self.loaded_to_maya:
            raise RuntimeError('Garment should be loaded when evaluating vertex segmentation')

        self.update_verts_info()
        self.vertex_labels = [None] * len(self.current_verts)

        # -- Stitches (provided in qualoth objects directly) ---
        on_stitches = self._verts_on_stitches()  # TODO I can even distinguish stitches from each other!
        for idx in on_stitches:
            self.vertex_labels[idx] = 'stitch'
        
        # --- vertices ---
        vertices = self.current_verts
        # BBoxes give fast results for most vertices
        bboxes = self._all_panel_bboxes() 
        vertices_multi_match = []
        for i in range(len(vertices)):
            if i in on_stitches:  # already labeled
                continue
            vertex = vertices[i]
            # check which panel is the closest one
            in_bboxes = []
            for panel in bboxes:
                if self._point_in_bbox(vertex, bboxes[panel]):
                    in_bboxes.append(panel)
            
            if len(in_bboxes) == 1:
                self.vertex_labels[i] = in_bboxes[0]
            else:  # multiple or zero matches -- handle later
                vertices_multi_match.append((i, in_bboxes))

        # eval for confusing cases
        neighbour_checks = 0
        while len(vertices_multi_match) > 0:
            unlabeled_vert_id, matched_panels = vertices_multi_match.pop(0)

            # check if vert in on the plane of any of the panels
            on_panel_planes = []
            for panel in matched_panels:
                if self._point_on_plane(vertices[unlabeled_vert_id], panel):
                    on_panel_planes.append(panel)

            # plane might not be the only option 
            if len(on_panel_planes) == 1:  # found!
                self.vertex_labels[unlabeled_vert_id] = on_panel_planes[0]
            else:
                # by this time, many vertices already have labels, so let's just borrow from neigbours
                neighbors = self._get_vert_neighbours(unlabeled_vert_id)

                neighbour_checks += 1

                if len(neighbors) == 0:
                    # print('Skipped Vertex {} with zero neigbors'.format(unlabeled_vert_id))
                    continue

                unlabelled = [unl[0] for unl in vertices_multi_match]
                # check only labeled neigbors that are not on stitches
                neighbors = [vert_id for vert_id in neighbors if vert_id not in unlabelled and vert_id not in on_stitches]

                if len(neighbors) > 0:
                    neighbour_labels = [self.vertex_labels[vert_id] for vert_id in neighbors]
                    
                    # https://www.geeksforgeeks.org/python-find-most-frequent-element-in-a-list
                    frequent_label = max(set(neighbour_labels), key=neighbour_labels.count)
                    self.vertex_labels[unlabeled_vert_id] = frequent_label
                else:
                    # put back 
                    # NOTE! There is a ponetial for infinite loop here, but it shoulf not occur
                    # if the garment is freshly loaded before sim
                    print('Garment::Labelling::vertex {} needs revisit'.format(unlabeled_vert_id))
                    vertices_multi_match.append((unlabeled_vert_id, on_panel_planes))

    def _clean_mesh(self):
        """
            Clean mesh from incosistencies introduces by stitching, 
            and update vertex-dependednt info accordingly
        """
        # remove the junk after garment was stitched and labeled
        cmds.polyClean(self.get_qlcloth_geomentry())

        # fix labeling
        self.update_verts_info()
        match_verts = utils.match_vert_lists(self.current_verts, self.last_verts)

        self.vertex_labels = [self.vertex_labels[i] for i in match_verts]

    def _edge_as_3d_tuple_list(self, edge, vertices):
        """
            Represents given edge object as list of control points
            suitable for draing in Maya
        """
        points = vertices[edge['endpoints'], :]
        if 'curvature' in edge:
            control_coords = self._control_to_abs_coord(
                points[0], points[1], edge['curvature']
            )
            # Rearrange
            points = np.r_[
                [points[0]], [control_coords], [points[1]]
            ]
        # to 3D
        points = np.c_[points, np.zeros(len(points))]

        return list(map(tuple, points))

    def _applyEuler(self, vector, eulerRot):
        """Applies Euler angles (in degrees) to provided 3D vector"""
        # https://www.cs.utexas.edu/~theshark/courses/cs354/lectures/cs354-14.pdf
        eulerRot_rad = np.deg2rad(eulerRot)
        # X 
        vector_x = np.copy(vector)
        vector_x[1] = vector[1] * np.cos(eulerRot_rad[0]) - vector[2] * np.sin(eulerRot_rad[0])
        vector_x[2] = vector[1] * np.sin(eulerRot_rad[0]) + vector[2] * np.cos(eulerRot_rad[0])

        # Y
        vector_y = np.copy(vector_x)
        vector_y[0] = vector_x[0] * np.cos(eulerRot_rad[1]) + vector_x[2] * np.sin(eulerRot_rad[1])
        vector_y[2] = -vector_x[0] * np.sin(eulerRot_rad[1]) + vector_x[2] * np.cos(eulerRot_rad[1])

        # Z
        vector_z = np.copy(vector_y)
        vector_z[0] = vector_y[0] * np.cos(eulerRot_rad[2]) - vector_y[1] * np.sin(eulerRot_rad[2])
        vector_z[1] = vector_y[0] * np.sin(eulerRot_rad[2]) + vector_y[1] * np.cos(eulerRot_rad[2])

        return vector_z

    def _set_panel_3D_attr(self, panel_dict, panel_group, attribute, maya_attr):
        """Set recuested attribute to value from the spec"""
        if attribute in panel_dict:
            values = panel_dict[attribute]
        else:
            values = [0, 0, 0]
        cmds.setAttr(
            panel_group + '.' + maya_attr, 
            values[0], values[1], values[2],
            type='double3')

    def _apply_panel_3d_placement(self, panel_name):
        """Apply transform from spec to given panel"""
        panel = self.pattern['panels'][panel_name]
        panel_group = self.MayaObjects['panels'][panel_name]['curve_group']

        # set pivot to origin relative to currently loaded curves
        cmds.xform(panel_group, pivots=[0, 0, 0], worldSpace=True)

        # now place correctly
        self._set_panel_3D_attr(panel, panel_group, 'translation', 'translate')
        self._set_panel_3D_attr(panel, panel_group, 'rotation', 'rotate')

    def _maya_curve_name(self, address):
        """ Shortcut to retrieve the name of curve corresponding to the edge"""
        panel_name = address['panel']
        edge_id = address['edge']
        return self.MayaObjects['panels'][panel_name]['edges'][edge_id]

    def _save_to_path(self, path, filename):
        """Save current state of cloth object to given path with given filename"""
        
        # geometry
        filepath = os.path.join(path, filename + '.obj')
        utils.save_mesh(self.get_qlcloth_geomentry(), filepath)

        # segmentation
        filepath = os.path.join(path, filename + '_segmentation.txt')
        with open(filepath, 'w') as f:
            for panel_name in self.vertex_labels:
                f.write("%s\n" % panel_name)

        # eval
        num_verts = cmds.polyEvaluate(self.get_qlcloth_geomentry(), v=True)
        if num_verts != len(self.vertex_labels):
            print('MayaGarment::WARNING::Segmentation list does not match mesh topology in save {}'.format(self.name))
        
    def _intersect_object(self, geometry):
        """Check if given object intersects current cloth geometry
            Function does not have side-effects on input geometry"""
        
        # ray-based intersection test
        
        cloth_mesh, cloth_dag = utils.get_mesh_dag(self.get_qlcloth_geomentry())
        obstacle_mesh, obstacle_dag = utils.get_mesh_dag(geometry)

        # use obstacle verts as a base for testing
        # Assuming that the obstacle geometry has a lower resolution then the garment
        
        obs_vertices = OpenMaya.MPointArray()
        obstacle_mesh.getPoints(obs_vertices, OpenMaya.MSpace.kWorld)
        
        # use ray intersect of all edges of obstacle mesh with the garment mesh
        num_edges = obstacle_mesh.numEdges()
        accelerator = cloth_mesh.autoUniformGridParams()
        hit_border_length = 0  # those are edges along the border of intersecting area on the geometry
        for edge_id in range(num_edges):
            # Vertices that comprise an edge
            vtx1, vtx2 = utils.edge_vert_ids(obstacle_mesh, edge_id)

            # test intersection
            raySource = OpenMaya.MFloatPoint(obs_vertices[vtx1])
            rayDir = OpenMaya.MFloatVector(obs_vertices[vtx2] - obs_vertices[vtx1])
            hit = utils.test_ray_intersect(cloth_mesh, raySource, rayDir, accelerator)
            if hit: 
                # A very naive approximation of total border length of areas of intersection
                hit_border_length += rayDir.length()  

        if hit_border_length < 1e-5:  # no intersections -- no need for threshold check
            print('{} with {} do not intersect'.format(geometry, self.name))
            return False

        if ('object_intersect_border_threshold' in self.config 
                and hit_border_length > self.config['object_intersect_border_threshold']
                or (hit_border_length > 1e-5 and 'object_intersect_border_threshold' not in self.config)):  # non-zero hit if no threshold provided
            print('{} with {} intersect::Approximate intersection border length {:.2f} cm is above threshold {:.2f} cm'.format(
                geometry, self.name, hit_border_length, 
                self.config['object_intersect_border_threshold'] if 'object_intersect_border_threshold' in self.config else 0))
            return True
        
        print('{} with {} intersect::Approximate intersection border length {:.2f} cm is ignored by threshold {:.2f} cm'.format(
            geometry, self.name, hit_border_length, 
            self.config['object_intersect_border_threshold'] if 'object_intersect_border_threshold' in self.config else 0))
        return False

    def _verts_on_stitches(self):
        """
            List all the vertices in garment mesh located on stitches
            NOTE: it does not output vertices correctly on is the mesh topology was changed 
                (e.g. after cmds.polyClean())!!
        """
        on_stitches = []
        for stitch in self.pattern['stitches']:
            # querying one side is enough since they share the vertices
            for side in [0, 1]:
                stitch_curve = self._maya_curve_name(stitch[side]) 
                panel_name = stitch[side]['panel']
                panel_node = self.MayaObjects['panels'][panel_name]['qlPattern']

                verts_on_curve = qw.getVertsOnCurve(panel_node, stitch_curve)

                on_stitches += verts_on_curve
        return on_stitches
    
    def _verts_on_curves(self):
        """
            List all the vertices of garment mesh that are located on panel curves
        """
        all_edge_verts = []
        for panel in self.panel_order():
            panel_info = self.MayaObjects['panels'][panel]
            panel_node = panel_info['qlPattern']

            # curves
            for curve in panel_info['edges']:
                verts_on_curve = qw.getVertsOnCurve(panel_node, curve)
                all_edge_verts += verts_on_curve
    
                print(min(verts_on_curve), max(verts_on_curve))

        # might contain duplicates
        return all_edge_verts

    def _all_panel_bboxes(self):
        """
            Evaluate 3D bounding boxes for all panels (as original curve loops)
        """
        panel_curves = self.MayaObjects['panels']
        bboxes = {}
        for panel in panel_curves:
            box = cmds.exactWorldBoundingBox(panel_curves[panel]['curve_group'])
            bboxes[panel] = box
        return bboxes

    @staticmethod
    def _point_in_bbox(point, bbox, tol=0.01):
        """
            Check if point is within bbox
            bbbox given in maya format (float[]	xmin, ymin, zmin, xmax, ymax, zmax.)
            NOTE: tol value is needed for cases when BBox collapses to 2D
        """
        if (point[0] < (bbox[0] - tol) or point[0] > (bbox[3] + tol)
                or point[1] < (bbox[1] - tol) or point[1] > (bbox[4] + tol)
                or point[2] < (bbox[2] - tol) or point[2] > (bbox[5] + tol)):
            return False
        return True
    
    def _point_on_plane(self, point, panel, tol=0.001):
        """
            Check if a point belongs to the same plane as given in the curve group
        """
        # I could check by panel rotation and translation!!
        rot = self.pattern['panels'][panel]['rotation']
        transl = np.array(self.pattern['panels'][panel]['translation'])

        # default panel normal upon load, sign doesn't matter here
        normal = np.array([0., 0., 1.])  
        rotated_normal = self._applyEuler(normal, rot)

        dot_prod = np.dot(np.array(point) - transl, rotated_normal)

        return np.isclose(dot_prod, 0., atol=tol)

    def _point_in_curve(self, point, curve_group, tol=0.01):
        """
            Check if a point is inside a given closed curve region
            Assuming that the point is roughly in the same plane as the curve
        """
        # closed curve mid-point
        # shoot a ray (new linear curve) and check if it intersects with any of 
        pass

    def _get_vert_neighbours(self, vert_id):
        """
            List the neigbours of given vertex in current cloth mesh
        """
        mesh_name = self.get_qlcloth_geomentry()

        edges = cmds.polyListComponentConversion(
            mesh_name + '.vtx[%d]' % vert_id, 
            fromVertex=True, toEdge=True)

        neighbors = []
        for edge in edges:
            neighbor_verts_str = cmds.polyListComponentConversion(edge, toVertex=True)
            for neighbor_str in neighbor_verts_str:
                values = neighbor_str.split(']')[0].split('[')[-1]
                if ':' in values:
                    neighbors += [int(x) for x in values.split(':')]
                else:
                    neighbors.append(int(values))
        
        return list(set(neighbors))  # leave only unique

    def _panel_to_id(self, panel):
        """ 
            Panel label as integer given the name of the panel
        """
        return int(self.panel_order().index(panel) + 1)


class MayaGarmentWithUI(MayaGarment):
    """Extension of MayaGarment that can generate GUI for controlling the pattern"""
    def __init__(self, pattern_file, clean_on_die=False):
        super(MayaGarmentWithUI, self).__init__(pattern_file, clean_on_die)
        self.ui_top_layout = None
        self.ui_controls = {}
    
    def __del__(self):
        super(MayaGarmentWithUI, self).__del__()
        # looks like UI now contains links to garment instance (callbacks, most probably)
        # If destructor is called, the UI is already clean
         
        # if self.ui_top_layout is not None:
        #     self._clean_layout(self.ui_top_layout)

    # ------- UI Drawing routines --------
    def drawUI(self, top_layout=None):
        """ Draw pattern controls in the given layout
            For correct connection with Maya attributes, it's recommended to call for drawing AFTER garment.load()
        """
        if top_layout is not None:
            self.ui_top_layout = top_layout
        if self.ui_top_layout is None:
            raise ValueError('GarmentDrawUI::top level layout not found')

        self._clean_layout(self.ui_top_layout)

        cmds.setParent(self.ui_top_layout)

        # Pattern name
        cmds.textFieldGrp(label='Pattern:', text=self.name, editable=False, 
                          cal=[1, 'left'], cw=[1, 50])

        # load panels info
        cmds.frameLayout(
            label='Panel Placement',
            collapsable=True, borderVisible=True, collapse=True,
            mh=10, mw=10
        )
        if not self.loaded_to_maya:
            cmds.text(label='<To be displayed after geometry load>')
        else:
            for panel in self.pattern['panels']:
                panel_layout = cmds.frameLayout(
                    label=panel, collapsable=True, collapse=True, borderVisible=True, mh=10, mw=10,
                    expandCommand=partial(cmds.select, self.MayaObjects['panels'][panel]['curve_group']),
                    collapseCommand=partial(cmds.select, self.MayaObjects['panels'][panel]['curve_group'])
                )
                self._ui_3d_placement(panel)
                cmds.setParent('..')
        cmds.setParent('..')

        # Parameters
        cmds.frameLayout(
            label='Parameters',
            collapsable=True, borderVisible=True, collapse=True,
            mh=10, mw=10
        )
        self._ui_params(self.parameters, self.spec['parameter_order'])
        cmds.setParent('..')

        # constraints
        if 'constraints' in self.spec:
            cmds.frameLayout(
                label='Constraints',
                collapsable=True, borderVisible=True, collapse=True,
                mh=10, mw=10
            )
            self._ui_constraints(self.spec['constraints'], self.spec['constraint_order'])
            cmds.setParent('..')

        # fin
        cmds.setParent('..')
        
    def _clean_layout(self, layout):
        """Removes all of the childer from layout"""
        children = cmds.layout(layout, query=True, childArray=True)
        if children:
            cmds.deleteUI(children)

    def _ui_3d_placement(self, panel_name):
        """Panel 3D placement"""
        if not self.loaded_to_maya:
            cmds.text(label='<To be displayed after geometry load>')

        # Position
        cmds.attrControlGrp(
            attribute=self.MayaObjects['panels'][panel_name]['curve_group'] + '.translate', 
            changeCommand=partial(self._panel_placement_callback, panel_name, 'translation', 'translate')
        )

        # Rotation
        cmds.attrControlGrp(
            attribute=self.MayaObjects['panels'][panel_name]['curve_group'] + '.rotate', 
            changeCommand=partial(self._panel_placement_callback, panel_name, 'rotation', 'rotate')
        )

    def _ui_param_value(self, param_name, param_range, value, idx=None, tag=''):
        """Create UI elements to display range and control the param value"""
        # range 
        cmds.rowLayout(numberOfColumns=3)
        cmds.text(label='Range ' + tag + ':')
        cmds.floatField(value=param_range[0], editable=False)
        cmds.floatField(value=param_range[1], editable=False)
        cmds.setParent('..')

        # value
        value_field = cmds.floatSliderGrp(
            label='Value ' + tag + ':', 
            field=True, value=value, 
            minValue=param_range[0], maxValue=param_range[1], 
            cal=[1, 'left'], cw=[1, 45], 
            step=0.01
        )
        # add command with reference to current field
        cmds.floatSliderGrp(value_field, edit=True, 
                            changeCommand=partial(self._param_value_callback, param_name, idx, value_field))

    def _ui_params(self, params, order):
        """draw params UI"""
        # control
        cmds.button(label='To template state', 
                    backgroundColor=[227 / 256, 255 / 256, 119 / 256],
                    command=self._to_template_callback, 
                    ann='Snap all parameters to default values')
        cmds.button(label='Randomize', 
                    backgroundColor=[227 / 256, 186 / 256, 119 / 256],
                    command=self._param_randomization_callback, 
                    ann='Randomize all parameter values')

        # Parameters themselves
        for param_name in order:
            cmds.frameLayout(
                label=param_name, collapsable=True, collapse=True, mh=10, mw=10
            )
            # type 
            cmds.textFieldGrp(label='Type:', text=params[param_name]['type'], editable=False, 
                              cal=[1, 'left'], cw=[1, 30])

            # parameters might have multiple values
            values = params[param_name]['value']
            param_ranges = params[param_name]['range']
            if isinstance(values, list):
                ui_tags = ['X', 'Y', 'Z', 'W']
                for idx, (value, param_range) in enumerate(zip(values, param_ranges)):
                    self._ui_param_value(param_name, param_range, value, idx, ui_tags[idx])
            else:
                self._ui_param_value(param_name, param_ranges, values)

            # fin
            cmds.setParent('..')

    def _ui_constraints(self, constraints, order):
        """View basic info about specified constraints"""
        for constraint_name in order:
            cmds.textFieldGrp(
                label=constraint_name + ':', text=constraints[constraint_name]['type'], 
                editable=False, 
                cal=[1, 'left'], cw=[1, 90])

    def _quick_dropdown(self, options, chosen='', label=''):
        """Add a dropdown with given options"""
        menu = cmds.optionMenu(label=label)
        for option in options:
            cmds.menuItem(label=option)
        if chosen:
            cmds.optionMenu(menu, e=True, value=chosen)

        return menu

    # -------- Callbacks -----------
    def _to_template_callback(self, *args):
        """Returns current pattern to template state and 
        updates UI accordingly"""
        # update
        print('Pattern returns to origins..')
        self._restore_template()
        # update geometry in lazy manner
        if self.loaded_to_maya:
            self.load()
        # update UI in lazy manner
        self.drawUI()

    def _param_randomization_callback(self, *args):
        """Randomize parameter values & update everything"""
        self._randomize_pattern()
        
        # update geometry in lazy manner
        if self.loaded_to_maya:
            self.load()
            # update UI in lazy manner
            self.drawUI()

    def _param_value_callback(self, param_name, value_idx, value_field, *args):
        """Update pattern with new value"""
        # in case the try failes
        spec_backup = copy.deepcopy(self.spec)
        if isinstance(self.parameters[param_name]['value'], list):
            old_value = self.parameters[param_name]['value'][value_idx]
        else:
            old_value = self.parameters[param_name]['value']

        # restore template state -- params are interdependent
        # change cannot be applied independently by but should follow specified param order
        self._restore_template(params_to_default=False)

        # get value
        new_value = args[0]
        # save new value. No need to check ranges -- correct by UI
        if isinstance(self.parameters[param_name]['value'], list):
            self.parameters[param_name]['value'][value_idx] = new_value
        else:
            self.parameters[param_name]['value'] = new_value
        
        # reapply all parameters
        self._update_pattern_by_param_values()
        if self.is_self_intersecting():
            result = cmds.confirmDialog( 
                title='Restore from broken state', 
                message=('Warning: Some of the panels contain intersected edges after applying value {} to {}.' 
                         '\nDo you want to revert to previous state?' 
                         '\n\nNote: simulation in broken state might result in Maya crashing').format(new_value, param_name), 
                button=['Yes', 'No'], 
                defaultButton='Yes', cancelButton='No', dismissString='No')
            if result == 'Yes':
                self._restore(spec_backup)
                cmds.floatSliderGrp(value_field, edit=True, value=old_value)
                return  # No need to reload geometry -- nothing changed

        # update geometry in lazy manner
        if self.loaded_to_maya:
            self.load()
            # NOTE updating values in UI in this callback causes Maya crashes! 
            # Without update, the 3D placement UI gets disconnected from geometry but that's minor
            # self.drawUI()

    def _panel_placement_callback(self, panel_name, attribute, maya_attr):
        """Update pattern spec with tranlation/rotation info from Maya"""
        # get values
        values = cmds.getAttr(self.MayaObjects['panels'][panel_name]['curve_group'] + '.' + maya_attr)
        values = values[0]  # only one attribute requested

        # set values
        self.pattern['panels'][panel_name][attribute] = list(values)


class Scene(object):
    """
        Decribes scene setup that includes:
            * body object
            * floor
            * light(s) & camera(s)
        Assumes 
            * body the scene revolved aroung faces z+ direction
    """
    def __init__(self, body_obj, props, scenes_path='', clean_on_die=False):
        """
            Set up scene for rendering using loaded body as a reference
        """
        self.self_clean = clean_on_die

        self.props = props
        self.config = props['config']
        self.stats = props['stats']
        # load body to be used as a translation reference
        self._load_body(body_obj)

        # scene
        self._init_arnold()
        self.scene = {}
        if 'scene' in self.config:
            self._load_maya_scene(os.path.join(scenes_path, self.config['scene']))
        else:
            self._simple_scene_setup()

    def __del__(self):
        """Remove all objects related to current scene if requested on creation"""
        if self.self_clean:
            cmds.delete(self.body)
            cmds.delete(self.cameras)
            for key in self.scene:
                cmds.delete(self.scene[key])
                # garment color migh become invalid

    def _init_arnold(self):
        """Ensure Arnold objects are launched in Maya & init GPU rendering settings"""

        objects = cmds.ls('defaultArnoldDriver')
        if not objects:  # Arnold objects not found
            # https://arnoldsupport.com/2015/12/09/mtoa-creating-the-defaultarnold-nodes-in-scripting/
            print('Initialized Arnold')
            mtoa.core.createOptions()
        
        cmds.setAttr('defaultArnoldRenderOptions.renderDevice', 1)  # turn on GPPU rendering
        cmds.setAttr('defaultArnoldRenderOptions.render_device_fallback', 1)  # switch to CPU in case of failure
        cmds.setAttr('defaultArnoldRenderOptions.AASamples', 10)  # increase sampling for clean results

    def floor(self):
        return self.scene['floor']
    
    def cloth_SG(self):
        return self.scene['cloth_SG']

    def render(self, save_to, name='last'):
        """
            Makes a rendering of a current scene, and saves it to a given path
        """
        # https://forums.autodesk.com/t5/maya-programming/rendering-with-arnold-in-a-python-script/td-p/7710875
        # NOTE that attribute names depend on Maya version. These are for Maya2018-Maya2020
        im_size = self.config['resolution']
        
        # image setup
        old_setup = self._set_image_size(im_size, im_size[0]/im_size[1], im_size[0]/im_size[1])
        cmds.setAttr("defaultArnoldDriver.aiTranslator", "png", type="string")

        # fixing dark rendering problem
        # https://forums.autodesk.com/t5/maya-shading-lighting-and/output-render-w-color-management-is-darker-than-render-view/td-p/7207081
        cmds.colorManagementPrefs(e=True, outputTransformEnabled=True, outputUseViewTransform=True)

        # render all the cameras
        curr_frame = cmds.currentTime(query=True)
        start_time = time.time()
        for camera in self.cameras:
            print('Rendering from camera {}'.format(camera))

            camera_name = camera.split(':')[-1]  # list of one element if ':' is not found
            local_name = (name + '_' + camera_name) if name else camera_name
            filename = os.path.join(save_to, local_name)
            cmds.setAttr("defaultArnoldDriver.prefix", filename, type="string")

            cmds.arnoldRender(width=im_size[0], height=im_size[1], batch=True, frameSequence=curr_frame, camera=camera)
        
        self._set_image_size(*old_setup)  # restore settings    
        self.stats['render_time'][name] = time.time() - start_time

    def fetch_props_from_Maya(self):
        """Get properties records from Maya
            Note: it updates global config!"""
        # Update color settings
        self.config['garment_color'] = self._fetch_color(self.scene['cloth_shader'])
        

    # ------- Private -----------

    def _load_body(self, bodyfilename):
        """Load body object and scale it to cm units"""
        # load
        self.body_filepath = bodyfilename
        self.body = utils.load_file(bodyfilename, 'body')

        utils.scale_to_cm(self.body)

    def _fetch_color(self, shader):
        """Return current color of a given shader node"""
        return cmds.getAttr(shader + '.color')[0]

    def _simple_scene_setup(self):
        """setup very simple scene & materials"""
        colors = {
            "body_color": [0.5, 0.5, 0.7], 
            "cloth_color": [0.8, 0.2, 0.2] if 'garment_color' not in self.config else self.config['garment_color'],
            "floor_color": [0.8, 0.8, 0.8]
        }

        self.scene = {
            'floor': self._add_floor(self.body)
        }
        # materials
        self.scene['body_shader'], self.scene['body_SG'] = self._new_lambert(colors['body_color'], self.body)
        self.scene['cloth_shader'], self.scene['cloth_SG'] = self._new_lambert(colors['cloth_color'], self.body)
        self.scene['floor_shader'], self.scene['floor_SG'] = self._new_lambert(colors['floor_color'], self.body)

        self.scene['light'] = mutils.createLocator('aiSkyDomeLight', asLight=True)

        # Put camera
        self.cameras = [self._add_simple_camera()]

        # save config
        self.config['garment_color'] = colors['cloth_color']

    def _load_maya_scene(self, scenefile):
        """Load scene from external file. 
            NOTE Assumes certain naming of nodes in the scene!"""
        before = set(cmds.ls())
        cmds.file(scenefile, i=True, namespace='imported')
        new_objects = set(cmds.ls()) - before
        # Maya may modify namespace for uniquness
        scene_namespace = new_objects.pop().split(':')[0] + '::'  

        self.scene = {
            'scene_group': cmds.ls(scene_namespace + '*scene*', transforms=True)[0],
            'floor': cmds.ls(scene_namespace + '*floor*', geometry=True)[0],
            'body_shader': cmds.ls(scene_namespace + '*body*', materials=True)[0],
            'cloth_shader': cmds.ls(scene_namespace + '*garment*', materials=True, )[0]
        }
        # shader groups (to be used in cmds.sets())
        self.scene['body_SG'] = self._create_shader_group(self.scene['body_shader'], 'bodySG')
        self.scene['cloth_SG'] = self._create_shader_group(self.scene['cloth_shader'], 'garmentSG')

        if 'garment_color' in self.config:  # if given, use it
            color = self.config['garment_color']
            cmds.setAttr((self.scene['cloth_shader'] + '.color'), color[0], color[1], color[2], type='double3')
        else:
            # save garment color to config
            self.config['garment_color'] = self._fetch_color(self.scene['cloth_shader'])

        # apply coloring to body object
        if self.body:
            cmds.sets(self.body, forceElement=self.scene['body_SG'])

        # collect cameras
        self.cameras = cmds.ls(scene_namespace + '*camera*', transforms=True)

        # adjust scene position s.t. body is standing in the middle
        body_low_center = self._get_object_lower_center(self.body)
        floor_low_center = self._get_object_lower_center(self.scene['floor'])
        old_translation = cmds.getAttr(self.scene['scene_group'] + '.translate')[0]
        cmds.setAttr(
            self.scene['scene_group'] + '.translate',
            old_translation[0] + body_low_center[0] - floor_low_center[0],
            old_translation[1] + body_low_center[1] - floor_low_center[1], 
            old_translation[2] + body_low_center[2] - floor_low_center[2],
            type='double3')  # apply to whole group s.t. lights positions were adjusted too

    def _add_simple_camera(self, rotation=[-23.2, 16, 0]):
        """Puts camera in the scene
        NOTE Assumes body is facing +z direction"""

        camera = cmds.camera(aspectRatio=self.config['resolution'][0] / self.config['resolution'][1])[0]
        cmds.setAttr(camera + '.rotate', rotation[0], rotation[1], rotation[2], type='double3')

        # to view the target body
        fitFactor = self.config['resolution'][1] / self.config['resolution'][0]
        cmds.viewFit(camera, self.body, f=fitFactor)

        return camera

    def _get_object_lower_center(self, object):
        """return 3D position of the center of the lower side of bounding box"""
        bb = cmds.exactWorldBoundingBox(object)
        return [
            (bb[3] + bb[0]) / 2,
            bb[1],
            (bb[5] + bb[2]) / 2
        ]
    
    def _add_floor(self, target):
        """
            adds a floor under a given object
        """
        target_bb = cmds.exactWorldBoundingBox(target)

        size = 50 * (target_bb[4] - target_bb[1])
        floor = cmds.polyPlane(n='floor', w=size, h=size)

        # place under the body
        floor_level = target_bb[1]
        cmds.move((target_bb[3] + target_bb[0]) / 2,  # bbox center
                  floor_level, 
                  (target_bb[5] + target_bb[2]) / 2,  # bbox center
                  floor, a=1)

        # Make the floor non-renderable
        shape = cmds.listRelatives(floor[0], shapes=True)
        cmds.setAttr(shape[0] + '.primaryVisibility', 0)

        return floor[0]

    def _new_lambert(self, color, target=None):
        """created a new shader node with given color"""
        shader = cmds.shadingNode('lambert', asShader=True)
        cmds.setAttr((shader + '.color'), 
                     color[0], color[1], color[2],
                     type='double3')

        shader_group = self._create_shader_group(shader)
        if target is not None:
            cmds.sets(target, forceElement=shader_group)

        return shader, shader_group

    def _create_shader_group(self, material, name='shader'):
        """Create a shader group set for a given material (to be used in cmds.sets())"""
        shader_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name)
        cmds.connectAttr(material + '.outColor', shader_group + '.surfaceShader')
        return shader_group

    def _set_image_size(self, im_size, ar_pix, ar_device):
        """Set image size for rendering"""

        # remember the old settings to allow restoration
        old_ar_pix = cmds.getAttr("defaultResolution.pixelAspect")
        old_ar_device = cmds.getAttr("defaultResolution.deviceAspectRatio")

        old_size = [0, 0]
        old_size[0] = cmds.getAttr("defaultResolution.width")
        old_size[1] = cmds.getAttr("defaultResolution.height")

        cmds.setAttr("defaultResolution.width", im_size[0])
        cmds.setAttr("defaultResolution.height", im_size[1])
        cmds.setAttr("defaultResolution.pixelAspect", ar_pix)
        cmds.setAttr("defaultResolution.deviceAspectRatio", ar_device)

        return old_size, old_ar_pix, old_ar_device

