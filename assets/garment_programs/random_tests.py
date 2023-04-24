
""" Sample panels/components without a role to test stuff
"""

from copy import copy
import numpy as np

# Custom
import pypattern as pyp
from . import sleeves
from . import collars

# Curvy shape to try projections on


class CurvyPanel(pyp.Panel):
    def __init__(self, name, size=40) -> None:
        super().__init__(name)

        # self.edges = pyp.esf.from_verts(
        #     [0, 0], [0, size], [size, size], [size, 0]
        # )
        # TODO Creation shortcut
        # self.edges.append(pyp.CurveEdge([0, 0], [0, size], [[0.2, 0.3], [0.4, -0.2]]))
        self.edges.append(pyp.Edge([0, 0], [0, size]))
        # self.edges.append(pyp.CurveEdge(self.edges[-1].end, [size, size], [[0.5, 0.3]]))
        self.edges.append(pyp.CircleEdge(self.edges[-1].end, [size, size], cy=0.2))
        self.edges.append(pyp.CurveEdge(self.edges[-1].end, [size, 0], [[0.2, 0.3], [0.4, -0.2]]))
        # self.edges.append(pyp.Edge(self.edges[-1].end, [size, 0]))
        # self.edges.append(pyp.CurveEdge(self.edges[-1].end, self.edges[0].start, [[0.2, 0.3], [0.4, -0.2]]))
        self.edges.append(pyp.CircleEdge(self.edges[-1].end, self.edges[0].start, cy=-0.3))
        # STRAIGHT 
        # self.edges.append(pyp.Edge(self.edges[-1].end, self.edges[0].start))

        # # DEBUG subdivision

        # new_up_side = self.edges[1].subdivide([0.5697, 0.43028])
        # self.edges.substitute(1, new_up_side)
        # print(new_up_side[0].end)

        self.interfaces = {
            'left_corner': pyp.Interface(self, self.edges[:2]),
            'right_corner': pyp.Interface(self, self.edges[1:3])
        }

        print('DART')  # DEBUG
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(5, 15), self.edges[-1], 
            offset=self.edges[-1].length() / 2, right=True)
        
        # DEBUG
        print(self.edges)

        self.edges.substitute(-1, b_edge)

        # DEBUG
        print(self.edges)


class CurvyProjection(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        self.panel = CurvyPanel('panel') 

        print('SLEEVE')  # DEBUG
        self.sleeve = sleeves.Sleeve('curvy_projection', body, design, depth_diff=5)
        _, f_sleeve_int = pyp.ops.cut_corner(
            self.sleeve.interfaces['in_front_shape'].projecting_edges(), 
            self.panel.interfaces['left_corner'])
        
        if design['sleeve']['sleeveless']['v']:    # TODO Part of sleeve class??
            # No sleeve component, only the cut remains
            del self.sleeve

        print('COLLAR')  # DEBUG
        collar_type = getattr(collars, design['collar']['f_collar']['v'])
        f_collar = collar_type(
            design['collar']['fc_depth']['v'], 
            design['collar']['width']['v'], 
            angle=design['collar']['fc_angle']['v'])
        pyp.ops.cut_corner(f_collar, self.panel.interfaces['right_corner'])


        

