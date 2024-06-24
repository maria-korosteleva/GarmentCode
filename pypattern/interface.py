from copy import copy

from numpy.linalg import norm
import numpy as np

from pypattern.edge import EdgeSequence, Edge
from pypattern.generic_utils import close_enough


class Interface:
    """Description of an interface of a panel or component
        that can be used in stitches as a single unit
    """
    def __init__(self, panel, edges, ruffle=1.):
        """
        Parameters:
            * panel - Panel object
            * edges - Edge or EdgeSequence -- edges in the panel that are
                allowed to connect to
            * ruffle - ruffle coefficient for a particular edge. Interface
                object will supply projecting_edges() shape
                s.t. the ruffles with the given rate are created. Default = 1.
                    (no ruffles, smooth connection)
        """

        self.edges = edges if isinstance(edges, EdgeSequence) else EdgeSequence(edges)
        self.panel = [panel for _ in range(len(self.edges))]  # matches every edge 

        # Allow to enfoce change the direction of edge 
        # (used in many-to-many stitches correspondance determination)
        self.edges_flipping = [False for _ in range(len(self.edges))]

        # Ruffles are applied to sections
        # Since extending a chain of edges != extending each edge individually
        if isinstance(ruffle, list):
            assert len(ruffle) == len(edges), "Ruffles and Edges don't match"
            self.ruffle = []
            last_coef = None
            last_start = 0
            for i, coef in enumerate(ruffle):
                if coef == last_coef or last_coef is None:
                    last_coef = coef  # Making sure to overwrite None
                    continue
                self.ruffle.append(dict(coeff=last_coef, sec=[last_start, i]))
                last_start, last_coef = i, coef

            self.ruffle.append(dict(coeff=last_coef, sec=[last_start, len(ruffle)]))
                
        else:
            self.ruffle = [dict(coeff=ruffle, sec=[0, len(self.edges)])]

    def projecting_edges(self, on_oriented=False) -> EdgeSequence:
        """Return edges shape that should be used when projecting interface
            onto another panel
            NOTE: reflects current state of the edge object. Call this function
                again if egdes change (e.g. their direction)
        """
        # Per edge set ruffle application
        projected = self.edges.copy() if not on_oriented else self.oriented_edges()
        for r in self.ruffle:
            if not close_enough(r['coeff'], 1, 1e-3):
                projected[r['sec'][0]:r['sec'][1]].extend(1 / r['coeff'])
        
        return projected

    def needsFlipping(self, i):
        """ Check if particular edge (i) should be re-oriented to follow the
            general direction of the interface
            * tol -- tolerance in distance differences that triggers flipping (in cm)

        """
        return self.edges_flipping[i]

    # ANCHOR --- Info ----
    def oriented_edges(self):
        """ Orient the edges withing the interface sequence along the general
            direction of the interface

            Creates a copy of the interface s.t. not to disturb the original
                edge objects
        """
        # NOTE we cannot we do the same for the edge sub-sequences:
        #  - midpoint of a sequence is less representative
        #  - more likely to have weird relative 3D orientations
        # => heuristic won't work as well

        oriented = self.edges.copy()

        for i in range(len(self.edges)):
            if self.needsFlipping(i):
                oriented[i].reverse()
                oriented[i].flipped = True
            else:
                oriented[i].flipped = False
        return oriented

    def verts_3d(self):
        """Return 3D locations of all vertices that participate in the
            interface"""

        verts_2d = []
        matching_panels = []
        for e, panel in zip(self.edges, self.panel):
            if all(e.start is not v for v in verts_2d):  # Ensuring uniqueness
                verts_2d.append(e.start)
                matching_panels.append(panel)
            
            if all(e.end is not v for v in verts_2d):  # Ensuring uniqueness
                verts_2d.append(e.end)
                matching_panels.append(panel)

        # To 3D
        verts_3d = []
        for v, panel in zip(verts_2d, matching_panels):
            verts_3d.append(panel.point_to_3D(v))

        return np.asarray(verts_3d)

    def bbox_3d(self):
        """Return Interface bounding box"""

        # NOTE: Vertex repetitions don't matter for bbox evaluation
        verts_3d = []
        for e, panel in zip(self.edges, self.panel):
            # Using curve linearization for more accurate approximation of bbox
            lin_edges = e.linearize()  
            verts_2d = lin_edges.verts()
            verts_3d += [panel.point_to_3D(v) for v in verts_2d]
        verts_3d = np.asarray(verts_3d)

        return verts_3d.min(axis=0), verts_3d.max(axis=0)
        

    def __len__(self):
        return len(self.edges)
    
    def __str__(self) -> str:
        return f'Interface: {[p.name for p in self.panel]}: {str(self.oriented_edges())}'
    
    def __repr__(self) -> str:
        return self.__str__()

    def panel_names(self):
        return [p.name for p in self.panel]

    # ANCHOR --- Interface Updates -----

    def reverse(self, with_edge_dir_reverse=False):
        """Reverse the order of edges in the interface
            (without updating the edge objects)

            Reversal is useful for reordering interface edges for correct
                matching in the multi-stitches
        """
        self.edges.edges.reverse()   # TODOLOW Condition on edge sequence reverse 
        self.panel.reverse()
        self.edges_flipping.reverse()
        if with_edge_dir_reverse:
            self.edges_flipping = [not e for e in self.edges_flipping]

        enum = len(self.edges)
        for r in self.ruffle:
            # Update ids
            r['sec'][0] = enum - r['sec'][0]
            r['sec'][1] = enum - r['sec'][1]
            # Swap
            r['sec'][0], r['sec'][1] = r['sec'][1], r['sec'][0]
        
        return self

    def reorder(self, curr_edge_ids, projected_edge_ids):
        """Change the order of edges from curr_edge_ids to projected_edge_ids
            in the interface

            Note that the input should prescrive new ordering for all affected
            edges e.g. if moving 0 -> 1, specify the new location for 1 as well
        """
        
        # TODOLOW Edge Sequence Function wrapper?
        for i, j in zip(curr_edge_ids, projected_edge_ids):
            for r in self.ruffle:
                if (i >= r['sec'][0] and i < r['sec'][1] 
                        and (j < r['sec'][0] or j >= r['sec'][1])):
                    raise NotImplementedError(
                        f'{self.__class__.__name__}::ERROR::reordering between panel-related sub-segments is not supported')
        
        new_edges = EdgeSequence()
        new_panel_list = []
        new_flipping_info = []
        for i in range(len(self.panel)):
            id = i if i not in curr_edge_ids else projected_edge_ids[curr_edge_ids.index(i)]
            # edges
            new_edges.append(self.edges[id])
            new_flipping_info.append(self.edges_flipping[id])
            # panels
            new_panel_list.append(self.panel[id])
            
        self.edges = new_edges
        self.panel = new_panel_list
        self.edges_flipping = new_flipping_info

    def substitute(self, orig, new_edges, new_panels):
        """Update the interface edges with correct correction of panels
            * orig -- could be an edge object or the id of edges that need
                substitution
            * new_edges -- new edges to insert in place of orig
            * new_panels -- per-edge panel objects indicating where each of
                new_edges belong to
        
        NOTE: the ruffle indicator for the new_edges is expected to be the
            same as for orig edge
        Specifying new indicators is not yet supported

        """
        if isinstance(orig, Edge):
            orig = self.edges.index(orig)
        if orig < 0: 
            orig = len(self.edges) + orig 
        self.edges.substitute(orig, new_edges)

        # Update panels & flip info
        self.panel.pop(orig)
        curr_edges_flip = self.edges_flipping.pop(orig)
        if isinstance(new_panels, list) or isinstance(new_panels, tuple):
            for j in range(len(new_panels)):
                self.panel.insert(orig + j, new_panels[j])
                self.edges_flipping.insert(orig + j, curr_edges_flip)
        else: 
            self.panel.insert(orig, new_panels)
            self.edges_flipping.insert(orig, curr_edges_flip)

        # Propagate ruffle indicators
        ins_len = 1 if isinstance(new_edges, Edge) else len(new_edges)
        if ins_len > 1:
            for it in self.ruffle:  # UPD ruffle indicators
                if it['sec'][0] > orig:
                    it['sec'][0] += ins_len - 1
                if it['sec'][1] > orig:
                    it['sec'][1] += ins_len - 1

        return self

    # ANCHOR ----- Statics ----
    @staticmethod
    def from_multiple(*ints):
        """Create interface from other interfaces: 
            * Allows to use different panels in one interface
            * different ruffle values in one interface
            
            # NOTE the relative order of edges is preserved from the
            original interfaces and the incoming interface sequence
            This order will then be used in the SrtitchingRule when
            determing connectivity between interfaces
        """
        new_int = copy(ints[0])  # shallow copy -- don't create unnecessary objects
        new_int.edges = EdgeSequence()
        new_int.edges_flipping = []
        new_int.panel = []
        new_int.ruffle = []
        
        for elem in ints:
            shift = len(new_int.edges)
            new_int.ruffle += [copy(r) for r in elem.ruffle]
            for r in new_int.ruffle[-len(elem.ruffle):]:
                r.update(sec=[r['sec'][0] + shift, r['sec'][1] + shift])

            new_int.edges.append(elem.edges)
            new_int.panel += elem.panel 
            new_int.edges_flipping += elem.edges_flipping 
            
        return new_int 

    @staticmethod
    def _is_order_matching(panel_s, vert_s, panel_1, vert1, panel_2, vert2) -> bool:
        """Check which of the two vertices vert1 (panel_1) or vert2 (panel_2)
            is closer to the vert_s
            from panel_s in 3D"""
        s_3d = panel_s.point_to_3D(vert_s)
        v1_3d = panel_1.point_to_3D(vert1)
        v2_3d = panel_2.point_to_3D(vert2)

        return norm(v1_3d - s_3d) < norm(v2_3d - s_3d)
