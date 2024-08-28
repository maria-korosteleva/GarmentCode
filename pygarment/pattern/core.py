"""
    Module for basic operations on patterns
"""
# Basic
import copy
import errno
import json
import numpy as np
import os
import random
import svgpathtools as svgpath

# My
from . import rotation as rotation_tools
from . import utils

standard_filenames = [
    'specification',  # e.g. used by dataset generation
    'template', 
    'prediction'
]

pattern_spec_template = {
    'pattern': {
        'panels': {},
        'stitches': []
    },
    'parameters': {},
    'parameter_order': [],
    'properties': {  # these are to be ensured when pattern content is updated directly
        'curvature_coords': 'relative', 
        'normalize_panel_translation': False, 
        'normalized_edge_loops': True,  # will trigger edge loop normalization on reload
        'units_in_meter': 100  # cm
    }
}

panel_spec_template = {
    'translation': [ 0, 0, 0 ],
    'rotation': [ 0, 0, 0 ],
    'vertices': [],
    'edges': []
}

class EmptyPatternError(BaseException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

# ------------ Patterns --------
class BasicPattern(object):
    """Loading & serializing of a pattern specification in custom JSON format.
        Input:
            * Pattern template in custom JSON format
        Output representations: 
            * Pattern instance in custom JSON format 
                * In the current state
        
        Not implemented: 
            * Convertion to NN-friendly format
            * Support for patterns with darts
    """

    # ------------ Interface -------------

    def __init__(self, pattern_file=None):
        
        self.spec_file = pattern_file
        
        if pattern_file is not None: # load pattern from file
            self.path = os.path.dirname(pattern_file)
            self.name = BasicPattern.name_from_path(pattern_file)
            self.reloadJSON()
        else: # create empty pattern
            self.path = None
            self.name = self.__class__.__name__
            self.spec = copy.deepcopy(pattern_spec_template)
            self.pattern = self.spec['pattern']
            self.properties = self.spec['properties']  # mandatory part

    def reloadJSON(self):
        """(Re)loads pattern info from spec file. 
        Useful when spec is updated from outside"""
        if self.spec_file is None:
            print('BasicPattern::WARNING::{}::Pattern is not connected to any file. Reloadig from file request ignored.'.format(
                self.name
            ))
            return

        with open(self.spec_file, 'r') as f_json:
            self.spec = json.load(f_json)
        self.pattern = self.spec['pattern']
        self.properties = self.spec['properties']  # mandatory part

        # template normalization - panel translations and curvature to relative coords
        self._normalize_template()

    def serialize(self, path, to_subfolder=True, tag='', empty_ok=False):

        if not empty_ok and len(self.panel_order()) == 0:
            raise RuntimeError(f'{self.__class__.__name__}::ERROR::Asked to save an empty pattern')

        # log context
        if tag:
            tag = '_' + tag
        if to_subfolder:
            log_dir = os.path.join(path, self.name + tag)  # NOTE Added change
            try:
                os.makedirs(log_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            spec_file = os.path.join(log_dir, (self.name + tag + '_specification.json'))
        else:
            log_dir = path
            spec_file = os.path.join(path, (self.name + tag + '_specification.json'))

        # Save specification
        with open(spec_file, 'w') as f_json:
            json.dump(self.spec, f_json, indent=2)
        
        return log_dir

    @staticmethod
    def name_from_path(pattern_file):
        name = os.path.splitext(os.path.basename(pattern_file))[0]
        if name.endswith('_specification'):
            name = name.split('_specification')[0]
        if name in standard_filenames:  # use name of directory instead
            path = os.path.dirname(pattern_file)
            name = os.path.basename(os.path.normpath(path))
        return name

    # --------- Info ------------------------
    def panel_order(self, force_update=False):
        """
            Return current agreed-upon order of panels
            * if not defined in the pattern or if  'force_update' is enabled, re-evaluate it based on curent panel translation and save
        """
        if 'panel_order' not in self.pattern or force_update:
            self.pattern['panel_order'] = self.define_panel_order()
        return self.pattern['panel_order']

    def define_panel_order(self, name_list=None, location_dict=None, dim=0, tolerance=10):
        """ (Recursive) Ordering of the panels based on their 3D translation values.
            * Using cm as units for tolerance (when the two coordinates are considered equal)
            * Sorting by all dims as keys X -> Y -> Z (left-right (looking from Z) then down-up then back-front)
            * based on the fuzzysort suggestion here https://stackoverflow.com/a/24024801/11206726"""

        if name_list is None:  # start from beginning
            name_list = self.pattern['panels'].keys() 
        if not name_list:
            return []
        if location_dict is None:  # obtain location for all panels to use in sorting further
            location_dict = {}
            for name in name_list:
                location_dict[name], _ = self._panel_universal_transtation(name)

        # consider only translations of the requested panel names
        reference = [location_dict[panel_n][dim] for panel_n in name_list]
        sorted_couple = sorted(zip(reference, name_list))  # sorts according to the first list
        sorted_reference, sorted_names = zip(*sorted_couple)
        sorted_names = list(sorted_names)

        if (dim + 1) < 3:  # 3D is max
            # re-sort values by next dimention if they have similar values in current dimention
            fuzzy_start, fuzzy_end = 0, 0  # init both in case we start from 1 panel to sort
            for fuzzy_end in range(1, len(sorted_reference)):
                if sorted_reference[fuzzy_end] - sorted_reference[fuzzy_start] >= tolerance:
                    # the range of similar values is completed
                    if fuzzy_end - fuzzy_start > 1:
                        sorted_names[fuzzy_start:fuzzy_end] = self.define_panel_order(
                            sorted_names[fuzzy_start:fuzzy_end], location_dict, dim + 1, tolerance)
                    fuzzy_start = fuzzy_end  # start counting similar values anew

            # take care of the tail
            if fuzzy_start != fuzzy_end:
                sorted_names[fuzzy_start:] = self.define_panel_order(
                    sorted_names[fuzzy_start:], location_dict, dim + 1, tolerance)

        return sorted_names

    # -- sub-utils --
    def _edge_as_vector(self, vertices, edge_dict):
        """Represent edge as vector of fixed length: 
            * First 2 elements: Vector endpoint. 
                Original edge endvertex positions can be restored if edge vector is added to the start point,
                which in turn could be obtained from previous edges in the panel loop
            * Next 2 elements: Curvature values 
                Given in relative coordinates. With zeros if edge is not curved 

        """
        edge_verts = vertices[edge_dict['endpoints']]
        edge_vector = edge_verts[1] - edge_verts[0]
        curvature = np.array(edge_dict['curvature']) if 'curvature' in edge_dict else [0, 0]

        return np.concatenate([edge_vector, curvature])

    def _edge_as_curve(self, vertices, edge):
        start = vertices[edge['endpoints'][0]]
        end = vertices[edge['endpoints'][1]]
        if ('curvature' in edge):
            # NOTE: supports old curves
            if isinstance(edge['curvature'], list) or edge['curvature']['type'] == 'quadratic':  
                control_scale = self._flip_y(edge['curvature'] if isinstance(edge['curvature'], list) else edge['curvature']['params'][0])
                control_point = utils.rel_to_abs_2d(start, end, control_scale)
                return svgpath.QuadraticBezier(*utils.list_to_c([start, control_point, end]))
            elif edge['curvature']['type'] == 'circle':  # Assuming circle
                # https://svgwrite.readthedocs.io/en/latest/classes/path.html#svgwrite.path.Path.push_arc

                radius, large_arc, right = edge['curvature']['params']

                return svgpath.Arc(
                    utils.list_to_c(start), radius + 1j*radius,
                    rotation=0,
                    large_arc=large_arc, 
                    sweep=not right,
                    end=utils.list_to_c(end)
                )

            elif edge['curvature']['type'] == 'cubic':
                cps = []
                for p in edge['curvature']['params']:
                    control_scale = self._flip_y(p)
                    control_point = utils.rel_to_abs_2d(start, end, control_scale)
                    cps.append(control_point)

                return svgpath.CubicBezier(*utils.list_to_c([start, *cps, end]))

            else:
                raise NotImplementedError(f'{self.__class__.__name__}::Unknown curvature type {edge["curvature"]["type"]}')

        else:
            return svgpath.Line(*utils.list_to_c([start, end]))

    @staticmethod
    def _point_in_3D(local_coord, rotation, translation):
        """Apply 3D transformation to the point given in 2D local coordinated, e.g. on the panel
        * rotation is expected to be given in 'xyz' Euler anges (as in Autodesk Maya) or as 3x3 matrix"""

        # 2D->3D local
        local_coord = np.append(local_coord, 0)

        # Rotate
        rotation = np.array(rotation)
        if rotation.size == 3:  # transform Euler angles to matrix
            rotation = rotation_tools.euler_xyz_to_R(rotation)
            # otherwise we already have the matrix
        elif rotation.size != 9:
            raise ValueError('BasicPattern::ERROR::You need to provide Euler angles or Rotation matrix for _point_in_3D(..)')
        rotated_point = rotation.dot(local_coord)

        # translate
        return rotated_point + translation

    def _panel_universal_transtation(self, panel_name):
        """Return a universal 3D translation of the panel (e.g. to be used in judging the panel order).
            Universal translation it defined as world 3D location of mid-point of the top (in 3D) of the panel (2D) bounding box.
            * Assumptions: 
                * In most cases, top-mid-point of a panel corresponds to body landmarks (e.g. neck, middle of an arm, waist) 
                and thus is mostly stable across garment designs.
                * 3D location of a panel is placing this panel around the body in T-pose
            * Function result is independent from the current choice of the local coordinate system of the panel
        """
        panel = self.pattern['panels'][panel_name]
        vertices = np.array(panel['vertices'])

        # out of 2D bounding box sides' midpoints choose the one that is highest in 3D
        top_right = vertices.max(axis=0)
        low_left = vertices.min(axis=0)
        mid_x = (top_right[0] + low_left[0]) / 2
        mid_y = (top_right[1] + low_left[1]) / 2
        mid_points_2D = [
            [mid_x, top_right[1]], 
            [mid_x, low_left[1]],
            [top_right[0], mid_y],
            [low_left[0], mid_y]
        ]
        rot_matrix = rotation_tools.euler_xyz_to_R(panel['rotation'])  # calculate once for all points 
        mid_points_3D = np.vstack(tuple(
            [self._point_in_3D(coords, rot_matrix, panel['translation']) for coords in mid_points_2D]
        ))
        top_mid_point = mid_points_3D[:, 1].argmax()

        return mid_points_3D[top_mid_point], np.array(mid_points_2D[top_mid_point])

    # --------- Pattern operations (changes inner dicts) ----------
    def _normalize_template(self):
        """
        Updated template definition for convenient processing:
            * Converts curvature coordinates to realitive ones (in edge frame) -- for easy length scaling
            * snaps each panel center to (0, 0) if requested in props
            * scales everything to cm
        """
        if self.properties['curvature_coords'] == 'absolute':
            for panel in self.pattern['panels']:
                # convert curvature 
                vertices = self.pattern['panels'][panel]['vertices']
                edges = self.pattern['panels'][panel]['edges']
                for edge in edges:
                    if 'curvature' in edge:
                        edge['curvature'] = utils.abs_to_rel_2d(
                            vertices[edge['endpoints'][0]], 
                            vertices[edge['endpoints'][1]], 
                            edge['curvature']
                        )
            # now we have new property
            self.properties['curvature_coords'] = 'relative'
        
        if 'units_in_meter' in self.properties:
            if self.properties['units_in_meter'] != 100:
                for panel in self.pattern['panels']:
                    self._normalize_panel_scaling(panel, self.properties['units_in_meter'])
                # now we have cm
                self.properties['original_units_in_meter'] = self.properties['units_in_meter']
                self.properties['units_in_meter'] = 100
                print('WARNING: pattern units converted to cm')
        else:
            print('WARNING: units not specified in the pattern. Scaling normalization was not applied')

        # after curvature is converted!!
        # Only if requested
        if ('normalize_panel_translation' in self.properties 
                and self.properties['normalize_panel_translation']):
            print('Normalizing translation!')
            self.properties['normalize_panel_translation'] = False  # one-time use property. Preverts rotation issues on future reads
            for panel in self.pattern['panels']:
                # put origin in the middle of the panel-- 
                offset = self._normalize_panel_translation(panel)
                # udpate translation vector
                original = self.pattern['panels'][panel]['translation'] 
                self.pattern['panels'][panel]['translation'] = [
                    original[0] + offset[0], 
                    original[1] + offset[1], 
                    original[2], 
                ]

        # Recalculate origins and traversal order of panel edge loops if not normalized already
        if ('normalized_edge_loops' not in self.properties
                or not self.properties['normalized_edge_loops']):
            print('{}::WARNING::normalizing the order and origin choice for edge loops in panels'.format(self.__class__.__name__))
            self.properties['normalized_edge_loops'] = True
            for panel in self.pattern['panels']:
                self._normalize_edge_loop(panel)
        
        # Recalculate panel order if not given already
        self.panel_order()

    def _normalize_panel_translation(self, panel_name):
        """ Convert panel vertices to local coordinates: 
            Shifts all panel vertices s.t. origin is at the center of the panel
        """
        panel = self.pattern['panels'][panel_name]
        vertices = np.asarray(panel['vertices'])
        offset = np.mean(vertices, axis=0)
        vertices = vertices - offset

        panel['vertices'] = vertices.tolist()

        return offset
    
    def _normalize_panel_scaling(self, panel_name, units_in_meter):
        """Convert all panel info to cm. I assume that curvature is alredy converted to relative coords -- scaling does not need update"""
        scaling = 100 / units_in_meter
        # vertices
        vertices = np.array(self.pattern['panels'][panel_name]['vertices'])
        vertices = scaling * vertices
        self.pattern['panels'][panel_name]['vertices'] = vertices.tolist()

        # translation
        translation = self.pattern['panels'][panel_name]['translation']
        self.pattern['panels'][panel_name]['translation'] = [scaling * coord for coord in translation]

    def _normalize_edge_loop(self, panel_name):
        """
            * Re-order edges s.t. the edge loop starts from low-left vertex
            * Make the edge loop follow counter-clockwise direction (uniform traversal)
        """
        panel = self.pattern['panels'][panel_name]
        vertices = np.array(panel['vertices'])

        # Loop Origin
        loop_origin_id = self._vert_at_left_corner(vertices)
        print('{}:{}: Origin: {} -> {}'.format(
            self.name, panel_name, panel['edges'][0]['endpoints'][0], loop_origin_id))

        rotated_edges, rotated_edge_ids = self._rotate_edges(
            panel['edges'], list(range(len(panel['edges']))), loop_origin_id)
        panel['edges'] = rotated_edges

        # Panel flip for uniform edge loop order (and normal direction)
        first_edge = self._edge_as_vector(vertices, rotated_edges[0])[:2]
        last_edge = self._edge_as_vector(vertices, rotated_edges[-1])[:2]
        flipped = False
        # due to the choice of origin (at the corner), first & last edge cross-product will reliably show panel normal direction 
        if np.cross(first_edge, last_edge) > 0:  # should be negative -- counterclockwise
            print('{}::{}::panel <{}> flipped'.format(
                self.__class__.__name__, self.name, panel_name
            ))
            flipped = True

            # Vertices
            vertices[:, 0] = - vertices[:, 0]  # flip by X coordinate -- we'll rotate around Y
            panel['vertices'] = vertices.tolist()

            # Edges
            # new loop origin after update
            loop_origin_id = self._vert_at_left_corner(vertices)
            print('{}:{}: Origin: {} -> {}'.format(
                self.name, panel_name, panel['edges'][0]['endpoints'][0], loop_origin_id))

            rotated_edges, rotated_edge_ids = self._rotate_edges(rotated_edges, rotated_edge_ids, loop_origin_id)
            panel['edges'] = rotated_edges
            # update the curvatures in edges as they changed left\right symmetry in 3D
            for edge_id in range(len(rotated_edges)):
                if 'curvature' in panel['edges'][edge_id]:
                    curvature = panel['edges'][edge_id]['curvature']
                    # YES!! Only one of the curvature coordinates need update at this point
                    panel['edges'][edge_id]['curvature'][1] = -curvature[1]

            # Panel translation and rotation -- local coord frame changed!
            panel['translation'][0] -= 2 * panel['translation'][0] 

            panel_R = rotation_tools.euler_xyz_to_R(panel['rotation'])
            flip_R = np.eye(3)
            flip_R[0, 0] = flip_R[2, 2] = -1  # by 180 around Y

            panel['rotation'] = rotation_tools.R_to_euler(panel_R * flip_R)

        # Stitches -- update the edge references according to the new ids
        if 'stitches' in self.pattern.keys():
            for stitch_id in range(len(self.pattern['stitches'])):
                for side_id in [0, 1]:
                    if self.pattern['stitches'][stitch_id][side_id]['panel'] == panel_name:
                        old_edge_id = self.pattern['stitches'][stitch_id][side_id]['edge']
                        self.pattern['stitches'][stitch_id][side_id]['edge'] = rotated_edge_ids[old_edge_id]

        return rotated_edge_ids, flipped

    # -- sub-utils --
    def _edge_length(self, panel, edge):
        panel = self.pattern['panels'][panel]
        v_id_start, v_id_end = tuple(panel['edges'][edge]['endpoints'])
        v_start, v_end = np.array(panel['vertices'][v_id_start]), \
            np.array(panel['vertices'][v_id_end])
        
        return np.linalg.norm(v_end - v_start)

    @staticmethod
    def _vert_at_left_corner(vertices):
        """
            Find, which vertex is in the left corner
            * Determenistic process
        """
        left_corner = np.min(vertices, axis=0)
        vertices = vertices - left_corner
        
        # choose the one closest to zero (=low-left corner) as new origin
        verts_norms = np.linalg.norm(vertices, axis=1)  # numpy 1.9+
        origin_id = np.argmin(verts_norms)

        return origin_id

    @staticmethod
    def _rotate_edges(edges, edge_ids, new_origin_id):
        """
            Rotate provided list of edges s.t. the first edge starts from vertex with id = new_origin_id
            Map old edge_ids to new ones accordingly
            * edges expects list of edges structures
        """

        first_edge_orig_id = [idx for idx, edge in enumerate(edges) if edge['endpoints'][0] == new_origin_id]

        first_edge_orig_id = first_edge_orig_id[0]
        rotated_edges = edges[first_edge_orig_id:] + edges[:first_edge_orig_id]

        # map from old ids to new ids
        rotated_edge_ids = edge_ids[(len(rotated_edges) - first_edge_orig_id):] + edge_ids[:(len(rotated_edges) - first_edge_orig_id)]

        return rotated_edges, rotated_edge_ids

    def _restore(self, backup_copy):
        """Restores spec structure from given backup copy 
            Makes a full copy of backup to avoid accidential corruption of backup
        """
        self.spec = copy.deepcopy(backup_copy)
        self.pattern = self.spec['pattern']
        self.properties = self.spec['properties']  # mandatory part

    # -------- Checks ------------
    def is_self_intersecting(self):
        """returns True if any of the pattern panels are self-intersecting"""
        return any(map(self._is_panel_self_intersecting, self.pattern['panels']))

    def _is_panel_self_intersecting(self, panel_name, n_vert_approximation=10):
        """Checks whatever a given panel contains intersecting edges
        """
        panel = self.pattern['panels'][panel_name]
        vertices = np.array(panel['vertices'])

        edge_curves = []  
        for e in panel['edges']:
            curve = self._edge_as_curve(vertices, e)

            if isinstance(curve, svgpath.Arc):
                # NOTE: Intersections for Arcs (Circle edge) fails in svgpathtools:
                # They are not well implemented in svgpathtools, see
                # https://github.com/mathandy/svgpathtools/issues/121
                # https://github.com/mathandy/svgpathtools/blob/fcb648b9bb9591d925876d3b51649fa175b40524/svgpathtools/path.py#L1960
                # Hence using linear approximation for robustness:
                n = n_vert_approximation + 1
                tvals = np.linspace(0, 1, n, endpoint=False)[1:]
                edge_verts = [curve.point(t) for t in tvals]
                edge_curves += [svgpath.Line(edge_verts[i], edge_verts[i + 1]) for i in range(n-1)]
            else:
                edge_curves.append(curve)

        # NOTE: simple pairwise checks of edges
        for i1 in range(0, len(edge_curves)):
           for i2 in range(i1 + 1, len(edge_curves)):
                intersect_t = edge_curves[i1].intersect(edge_curves[i2])
                
                # Check exceptions -- intersection at the vertex
                for i in range(len(intersect_t)): 
                    t1, t2 = intersect_t[i]
                    if t2 < t1:
                        t1, t2 = t2, t1
                    if utils.close_enough(t1, 0) and utils.close_enough(t2, 1):
                        intersect_t[i] = None
                intersect_t = [el for el in intersect_t if el is not None]

                if intersect_t:  # Any other case of intersections
                    return True      
        return False 

# NOTE: Deprecated. Preserved for backward compatibility 
# with the first dataset of 3D garments and sewing patterns
class ParametrizedPattern(BasicPattern):
    """
        Extention to BasicPattern that can work with parametrized patterns
        Update pattern with new parameter values & randomize those parameters
    """
    def __init__(self, pattern_file=None):
        super().__init__(pattern_file)
        self.parameters = self.spec['parameters']

        self.parameter_defaults = {
            'length': 1,
            'additive_length': 0,
            'curve': 1
        }
        self.constraint_types = [
            'length_equality'
        ]

    def param_values_list(self):
        """Returns current values of all parameters as a list in the pattern defined parameter order"""
        value_list = []
        for parameter in self.spec['parameter_order']:
            value = self.parameters[parameter]['value']
            if isinstance(value, list):
                value_list += value
            else:
                value_list.append(value)
        return value_list

    def apply_param_list(self, values):
        """Apply given parameters supplied as a list of param_values_list() form"""

        self._restore_template(params_to_default=False)

        # set new values
        value_count = 0
        for parameter in self.spec['parameter_order']:
            last_value = self.parameters[parameter]['value']
            if isinstance(last_value, list):
                self.parameters[parameter]['value'] = [values[value_count + i] for i in range(len(last_value))]
                value_count += len(last_value)
            else:
                self.parameters[parameter]['value'] = values[value_count]
                value_count += 1
        
        self._update_pattern_by_param_values()

    def reloadJSON(self):
        """(Re)loads pattern info from spec file. 
        Useful when spec is updated from outside"""
        super().reloadJSON()

        self.parameters = self.spec['parameters']
        self._normalize_param_scaling()

    def _restore(self, backup_copy):
        """Restores spec structure from given backup copy 
            Makes a full copy of backup to avoid accidential corruption of backup
        """
        super()._restore(backup_copy)
        self.parameters = self.spec['parameters']
    
    # ---------- Parameters operations --------

    def _normalize_param_scaling(self):
        """Convert additive parameters to cm units"""

        if 'original_units_in_meter' in self.properties:    # pattern was scaled
            scaling = 100 / self.properties['original_units_in_meter']
            for parameter in self.parameters:
                if self.parameters[parameter]['type'] == 'additive_length': 
                    self.parameters[parameter]['value'] = scaling * self.parameters[parameter]['value']
                    self.parameters[parameter]['range'] = [
                        scaling * elem for elem in self.parameters[parameter]['range']
                    ]

            # now we have cm everywhere -- no need to keep units info
            self.properties.pop('original_units_in_meter', None)

            print('WARNING: Parameter units were converted to cm')

    def _normalize_edge_loop(self, panel_name):
        """Update the edge loops and edge ids references in parameters & constraints after change"""
        rotated_edge_ids, flipped = super()._normalize_edge_loop(panel_name)

        # Parameters
        for parameter_name in self.spec['parameters']:
            self._influence_after_edge_loop_update(
                self.spec['parameters'][parameter_name]['influence'], 
                panel_name, rotated_edge_ids)

        # Constraints
        if 'constraints' in self.spec:
            for constraint_name in self.spec['constraints']:
                self._influence_after_edge_loop_update(
                    self.spec['constraints'][constraint_name]['influence'], 
                    panel_name, rotated_edge_ids)

    def _influence_after_edge_loop_update(self, infl_list, panel_name, new_edge_ids):
        """
            Update the list of parameter\constraint influence with the new edge ids of given panel.
            
            flipped -- indicates if in the new edges start & end vertices have been swapped
        """
        for infl_id in range(len(infl_list)):
            if infl_list[infl_id]['panel'] == panel_name:
                # update
                edge_list = infl_list[infl_id]['edge_list']
                for edge_list_id in range(len(edge_list)):
                    if isinstance(edge_list[edge_list_id], int):  # Simple edge id lists in curvature params
                        old_id = edge_list[edge_list_id]
                        edge_list[edge_list_id] = new_edge_ids[old_id]
                    elif isinstance(edge_list[edge_list_id]['id'], list):  # Meta-edge in length parameters  & constraints
                        for i in range(len(edge_list[edge_list_id]['id'])):
                            old_id = edge_list[edge_list_id]['id'][i]
                            edge_list[edge_list_id]['id'][i] = new_edge_ids[old_id]
                    else:  # edge description in length parameters & constraints
                        old_id = edge_list[edge_list_id]['id']
                        edge_list[edge_list_id]['id'] = new_edge_ids[old_id]
                
    def _update_pattern_by_param_values(self):
        """
        Recalculates vertex positions and edge curves according to current
        parameter values
        (!) Assumes that the current pattern is a template:
                with all the parameters equal to defaults!
        """
        for parameter in self.spec['parameter_order']:
            value = self.parameters[parameter]['value']
            param_type = self.parameters[parameter]['type']
            if param_type not in self.parameter_defaults:
                raise ValueError("Incorrect parameter type. Alowed are "
                                 + self.parameter_defaults.keys())

            for panel_influence in self.parameters[parameter]['influence']:
                for edge in panel_influence['edge_list']:
                    if param_type == 'length':
                        self._extend_edge(panel_influence['panel'], edge, value)
                    elif param_type == 'additive_length':
                        self._extend_edge(panel_influence['panel'], edge, value, multiplicative=False)
                    elif param_type == 'curve':
                        self._curve_edge(panel_influence['panel'], edge, value)
        # finally, ensure secified constraints are held
        self._apply_constraints()    

    def _restore_template(self, params_to_default=True):
        """Restore pattern to it's state with all parameters having default values
            Recalculate vertex positions, edge curvatures & snap values to 1
        """
        # Follow process backwards
        self._invert_constraints()

        for parameter in reversed(self.spec['parameter_order']):
            value = self.parameters[parameter]['value']
            param_type = self.parameters[parameter]['type']
            if param_type not in self.parameter_defaults:
                raise ValueError("Incorrect parameter type. Alowed are "
                                 + self.parameter_defaults.keys())

            for panel_influence in reversed(self.parameters[parameter]['influence']):
                for edge in reversed(panel_influence['edge_list']):
                    if param_type == 'length':
                        self._extend_edge(panel_influence['panel'], edge, self._invert_value(value))
                    elif param_type == 'additive_length':
                        self._extend_edge(panel_influence['panel'], edge, 
                                          self._invert_value(value, multiplicative=False), 
                                          multiplicative=False)
                    elif param_type == 'curve':
                        self._curve_edge(panel_influence['panel'], edge, self._invert_value(value))
            
            # restore defaults
            if params_to_default:
                if isinstance(value, list):
                    self.parameters[parameter]['value'] = [self.parameter_defaults[param_type] for _ in value]
                else:
                    self.parameters[parameter]['value'] = self.parameter_defaults[param_type]

    def _extend_edge(self, panel_name, edge_influence, value, multiplicative=True):
        """
            Shrinks/elongates a given edge or edge collection of a given panel. Applies equally
            to straight and curvy edges tnks to relative coordinates of curve controls
            Expects
                * each influenced edge to supply the elongatoin direction
                * scalar scaling_factor
            'multiplicative' parameter controls the type of extention:
                * if True, value is treated as a scaling factor of the edge or edge projection -- default
                * if False, value is added to the edge or edge projection
        """
        if isinstance(value, list):
            raise ValueError("Multiple scaling factors are not supported")

        verts_ids, verts_coords, target_line, _ = self._meta_edge(panel_name, edge_influence)

        # calc extention pivot
        if edge_influence['direction'] == 'end':
            fixed = verts_coords[0]  # start is fixed
        elif edge_influence['direction'] == 'start':
            fixed = verts_coords[-1]  # end is fixed
        elif edge_influence['direction'] == 'both':
            fixed = (verts_coords[0] + verts_coords[-1]) / 2
        else:
            raise RuntimeError('Unknown edge extention direction {}'.format(edge_influence['direction']))

        # move verts 
        # * along target line that sits on fixed point (correct sign & distance along the line)
        verts_projection = np.empty(verts_coords.shape)
        for i in range(verts_coords.shape[0]):
            verts_projection[i] = (verts_coords[i] - fixed).dot(target_line) * target_line

        if multiplicative:
            # * to match the scaled projection (correct point of application -- initial vertex position)
            new_verts = verts_coords - (1 - value) * verts_projection
        else:
            # * to match the added projection: 
            # still need projection to make sure the extention derection is corect relative to fixed point
            
            # normalize first
            for i in range(verts_coords.shape[0]):
                norm = np.linalg.norm(verts_projection[i])
                if not np.isclose(norm, 0):
                    verts_projection[i] /= norm

            # zero projections were not normalized -- they will zero-out the effect
            new_verts = verts_coords + value * verts_projection

        # update in the initial structure
        panel = self.pattern['panels'][panel_name]
        for ni, idx in enumerate(verts_ids):
            panel['vertices'][idx] = new_verts[ni].tolist()

    def _curve_edge(self, panel_name, edge, scaling_factor):
        """
            Updated the curvature of an edge accoding to scaling_factor.
            Can only be applied to edges with curvature information
            scaling_factor can be
                * scalar -- only the Y of control point is changed
                * 2-value list -- both coordinated of control are updated
        """
        panel = self.pattern['panels'][panel_name]
        if 'curvature' not in panel['edges'][edge]:
            raise ValueError('Applying curvature scaling to non-curvy edge '
                             + str(edge) + ' of ' + panel_name)
        control = panel['edges'][edge]['curvature']

        if isinstance(scaling_factor, list):
            control = [
                control[0] * scaling_factor[0],
                control[1] * scaling_factor[1]
            ]
        else:
            control[1] *= scaling_factor

        panel['edges'][edge]['curvature'] = control

    def _invert_value(self, value, multiplicative=True):
        """If value is a list, return a list with each value inverted.
            'multiplicative' parameter controls the type of inversion:
                * if True, returns multiplicative inverse (1/value) == default
                * if False, returns additive inverse (-value)
        """
        if multiplicative:
            if isinstance(value, list):
                if any(np.isclose(value, 0)):
                    raise ZeroDivisionError('Zero value encountered while restoring multiplicative parameter.')
                return map(lambda x: 1 / x, value)
            else:
                if np.isclose(value, 0):
                    raise ZeroDivisionError('Zero value encountered while restoring multiplicative parameter.')
                return 1 / value
        else:
            if isinstance(value, list):
                return map(lambda x: -x, value)
            else:
                return -value

    def _apply_constraints(self):
        """Change the pattern to adhere to constraints if given in pattern spec
            Assumes no zero-length edges exist"""
        if 'constraints' not in self.spec:
            return 

        for constraint_n in self.spec['constraints']:  # order preserved as it's a list
            constraint = self.spec['constraints'][constraint_n]
            constraint_type = constraint['type']
            if constraint_type not in self.constraint_types:
                raise ValueError("Incorrect constraint type. Alowed are "
                                 + self.constraint_types)

            if constraint_type == 'length_equality':
                # get all length of the affected (meta) edges
                target_len = []
                for panel_influence in constraint['influence']:
                    for edge in panel_influence['edge_list']:
                        # NOTE: constraints along a custom vector are not well tested
                        _, _, _, length = self._meta_edge(panel_influence['panel'], edge)
                        edge['length'] = length
                        target_len.append(length)
                if len(target_len) == 0:
                    return
                # target as mean of provided edges
                target_len = sum(target_len) / len(target_len)  

                # calculate scaling factor for every edge to match max length
                # & update edges with it
                for panel_influence in constraint['influence']:
                    for edge in panel_influence['edge_list']:
                        scaling = target_len / edge['length'] 
                        if not np.isclose(scaling, 1):
                            edge['value'] = scaling
                            self._extend_edge(panel_influence['panel'], edge, edge['value'])

    def _invert_constraints(self):
        """Restore pattern to the state before constraint was applied"""
        if 'constraints' not in self.spec:
            return 

        # follow the process backwards
        for constraint_n in reversed(self.spec['constraint_order']):  # order preserved as it's a list
            constraint = self.spec['constraints'][constraint_n]
            constraint_type = constraint['type']
            if constraint_type not in self.constraint_types:
                raise ValueError("Incorrect constraint type. Alowed are "
                                 + self.constraint_types)

            if constraint_type == 'length_equality':
                # update edges with invertes scaling factor
                for panel_influence in constraint['influence']:
                    for edge in panel_influence['edge_list']:
                        scaling = self._invert_value(edge['value'])
                        self._extend_edge(panel_influence['panel'], edge, scaling)
                        edge['value'] = 1

    def _meta_edge(self, panel_name, edge_influence):
        """Returns info for the given edge or meta-edge in inified form"""

        panel = self.pattern['panels'][panel_name]
        edge_ids = edge_influence['id']
        if isinstance(edge_ids, list):
            # meta-edge
            # get all vertices in order
            verts_ids = [panel['edges'][edge_ids[0]]['endpoints'][0]]  # start
            for edge_id in edge_ids:
                verts_ids.append(panel['edges'][edge_id]['endpoints'][1])  # end vertices
        else:
            # single edge
            verts_ids = panel['edges'][edge_ids]['endpoints']

        verts_coords = []
        for idx in verts_ids:
            verts_coords.append(panel['vertices'][idx])
        verts_coords = np.array(verts_coords)

        # extention line
        if 'along' in edge_influence:
            target_line = edge_influence['along']
        else:
            target_line = verts_coords[-1] - verts_coords[0] 
        target_line = np.array(target_line, dtype=float)  # https://stackoverflow.com/questions/50625975/typeerror-ufunc-true-divide-output-typecode-d-could-not-be-coerced-to-pro

        if np.isclose(np.linalg.norm(target_line), 0):
            raise ZeroDivisionError('target line is zero ' + str(target_line))
        else:
            target_line /= np.linalg.norm(target_line)

        return verts_ids, verts_coords, target_line, target_line.dot(verts_coords[-1] - verts_coords[0])

    def _invalidate_all_values(self):
        """Sets all values of params & constraints to None if not set already
            Useful in direct updates of pattern panels"""

        updated_once = False
        for parameter in self.parameters:
            if self.parameters[parameter]['value'] is not None:
                self.parameters[parameter]['value'] = None
                updated_once = True
        
        if 'constraints' in self.spec:
            for constraint in self.spec['constraints']:
                for edge_collection in self.spec['constraints'][constraint]['influence']:
                    for edge in edge_collection['edge_list']:
                        if edge['value'] is not None: 
                            edge['value'] = None
                            updated_once = True
        if updated_once:
            # only display worning if some new invalidation happened
            print('ParametrizedPattern::WARNING::Parameter (& constraints) values are invalidated')

    # ---------- Randomization -------------
    def _randomize_pattern(self):
        """Robustly randomize current pattern"""
        # restore template state before making any changes to parameters
        self._restore_template(params_to_default=False)

        spec_backup = copy.deepcopy(self.spec)
        self._randomize_parameters()
        self._update_pattern_by_param_values()
        for _ in range(100):  # upper bound on trials to avoid infinite loop
            if not self.is_self_intersecting():
                break

            print('WARNING::Randomized pattern is self-intersecting. Re-try..')
            self._restore(spec_backup)
            # Try again
            self._randomize_parameters()
            self._update_pattern_by_param_values()

    def _new_value(self, param_range):
        """Random value within range given as an iteratable"""
        value = random.uniform(param_range[0], param_range[1])
        # prevent non-reversible zero values
        if abs(value) < 1e-2:
            value = 1e-2 * (-1 if value < 0 else 1)
        return value

    def _randomize_parameters(self):
        """
        Sets new random values for the pattern parameters
        Parameter type agnostic
        """
        for parameter in self.parameters:
            param_ranges = self.parameters[parameter]['range']

            # check if parameter has multiple values (=> multiple ranges) like for curves
            if isinstance(self.parameters[parameter]['value'], list): 
                values = []
                for param_range in param_ranges:
                    values.append(self._new_value(param_range))
                self.parameters[parameter]['value'] = values
            else:  # simple 1-value parameter
                self.parameters[parameter]['value'] = self._new_value(param_ranges)


