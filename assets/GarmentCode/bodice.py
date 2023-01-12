from copy import copy
import numpy as np

# Custom
import pypattern as pyp

# other assets
from . import sleeves
from . import collars

# DRAFT Tried proper back-front assymetry, but failed
class BodiceFrontHalfAsymm0(pyp.Panel):
    """Half of the front of the Fitted bodice pattern"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        ease = design['ease']['v'] / 4

        shoulder_width = body['sholder_w'] / 2  # TODO Also use?
        armscye_depth = body['armscye_depth']
        underbust_size = body['underbust'] / 4

        # sizes
        side_depth = body['waist_line']
        max_length = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2
        front_width = (body['bust'] - body['back_width'] - body['bust_points'] * 2) / 4 + body['bust_points'] + ease
        front_fraction = front_width / (body['bust'] + ease * 4)
        waist = (body['waist'] + ease*4) * front_fraction

        print('front: ', front_width, waist, front_fraction)  # DEBUG

        # bottom
        bottom_d_width = (body['bust'] - body['waist']) / 6
        bottom_width = waist + bottom_d_width
        bottom_d_depth = 0.8 * (side_depth - body['bust_line'])  # calculated value
        bottom_d_position = bust_point
    
        # Bottom dart as cutout -- for straight line
        b_edge = pyp.Edge([0, 0], [-bottom_width, 0])
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), b_edge, 
            offset=bottom_d_position, right=True)
        self.edges.append(b_edge)

        # side dart
        side_dart_from_top = body['bust_line']
        side_d_depth = 0.7 * (front_width - bust_point)    # NOTE: calculated value

        side_len = np.sqrt((side_depth - armscye_depth)**2 + (front_width - bottom_width)**2)
        dart_pos = np.sqrt((side_depth - side_dart_from_top)**2 + (front_width - bottom_width)**2)
        side_edges, _, side_interface, side_dart_stitch = pyp.esf.side_with_dart_by_len(
            self.edges[-1].end, [-front_width, max_length - armscye_depth], 
            target_len=side_len, depth=side_d_depth, dart_position=side_len - dart_pos,   # NOTE Assuming l_section is shorter
            right=True, 
            panel=self)

        self.edges.append(side_edges)

        # top and front -- close the pattern
        self.edges.append(pyp.Edge(self.edges[-1].end, [-shoulder_width, max_length]))
        side_interface.edges.append(self.edges[-1])
        self.edges.append(pyp.Edge(self.edges[-1].end, [0, max_length]))
        self.edges.close_loop()

        # Stitch the darts
        self.stitching_rules.append(side_dart_stitch)
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

        # default placement
        self.translate_by([0, 30 - max_length, 0])

        # Out interfaces
        # TODO Corner by reference self.sleeve_corner = [side_edges[-1], top_and_collar[0]]
        self.interfaces = {
            'outside': side_interface,
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': b_interface,
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

class BodiceFrontHalf(pyp.Panel):
    """Half of the front of the Fitted bodice pattern"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        ease = design['ease']['v'] / 4

        shoulder_width = body['sholder_w'] / 2  # TODO Also use?
        armscye_depth = body['armscye_depth']
        underbust_size = body['underbust'] / 4

        # sizes
        side_depth = body['waist_line']
        max_length = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2
        front_width = body['bust'] / 4 + ease
        waist = body['waist'] / 4 + ease

        print('front: ', front_width, waist)  # DEBUG

        # bottom
        bottom_d_width = (body['bust'] - body['waist']) / 6
        bottom_width = waist + bottom_d_width
        bottom_d_depth = 0.8 * (side_depth - body['bust_line'])  # calculated value
        bottom_d_position = bust_point
    
        # Bottom dart as cutout -- for straight line
        b_edge = pyp.Edge([0, 0], [-bottom_width, 0])
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), b_edge, 
            offset=bottom_d_position, right=True)
        self.edges.append(b_edge)

        # side dart
        side_dart_from_top = body['bust_line']
        side_d_depth = 0.8 * (front_width - bust_point)    # NOTE: calculated value
        side_edges, _, side_interface, side_dart_stitch = pyp.esf.side_with_dart_by_len(
            self.edges[-1].end, [-front_width, max_length], 
            target_len=side_depth, depth=side_d_depth, dart_position=side_depth - side_dart_from_top,   # NOTE Assuming l_section is shorter
            right=True, 
            panel=self)
        self.edges.append(side_edges)

        # top and front -- close the pattern
        self.edges.append(pyp.Edge(self.edges[-1].end, [0, max_length]))
        self.edges.close_loop()

        # Stitch the darts
        self.stitching_rules.append(side_dart_stitch)
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

        # default placement
        self.translate_by([0, 30 - max_length, 0])

        # Out interfaces
        # TODO Corner by reference self.sleeve_corner = [side_edges[-1], top_and_collar[0]]
        self.interfaces = {
            'outside': side_interface,
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, b_interface),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

class BodiceFrontHalfFlat(pyp.Panel):
    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        ease = design['ease']['v'] / 4

        shoulder_width = body['sholder_w'] / 2  # TODO Also use?
        armscye_depth = body['armscye_depth']
        underbust_size = body['underbust'] / 4

        # sizes
        side_len = body['waist_line']
        max_len = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2
        front_width = body['bust'] / 4 + ease
        waist = body['waist'] / 4 + ease

        print('front: ', front_width, waist)  # DEBUG

        self.edges = pyp.esf.from_verts(
            [0, 0], [-front_width, 0], [-front_width, max_len], [0, max_len], 
            loop=True
        )

        # Side dart
        side_dart_from_top = body['bust_line']
        side_d_depth = 0.85 * (front_width - bust_point)    # NOTE: calculated value 0.8
        side_d_width = max_len - side_len
        s_edge, s_dart_edges, side_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(side_d_width, side_d_depth), self.edges[1], 
            offset=side_len - side_dart_from_top + side_d_width / 2, right=True)
        self.edges.substitute(1, s_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, s_dart_edges[0]), pyp.Interface(self, s_dart_edges[1])))

        # Bottom dart
        bottom_d_width = front_width - waist
        bottom_d_depth = 0.9 * (side_len - body['bust_line'])  # calculated value 0.8
        bottom_d_position = bust_point

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)
        self.edges.substitute(0, b_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))


        # default placement
        self.translate_by([0, 30 - max_len, 0])

        # Interfaces
        self.interfaces = {
            'outside': pyp.Interface(self, side_interface),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, b_interface),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

class BodiceFrontHalfSide(pyp.Panel):
    def __init__(self, name, body, design, shoulder_incl) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        ease = design['ease']['v'] / 4

        shoulder_width = body['sholder_w'] / 2  # TODO Also use?
        armscye_depth = body['armscye_depth']
        underbust_size = body['underbust'] / 4

        # sizes
        side_len = body['waist_line']
        max_len = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2
        front_width = body['bust'] / 4 + ease
        waist = body['waist'] / 4 + ease

        print('front: ', front_width, waist)  # DEBUG


        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-front_width, 0], 
            [-front_width, max_len - armscye_depth], 
            [-front_width, max_len], 
            [0, max_len + shoulder_incl], 
            loop=True
        )

        # Side dart
        side_dart_from_top = body['bust_line']
        side_d_depth = 0.85 * (front_width - bust_point)    # NOTE: calculated value 0.8
        side_d_width = max_len - side_len
        s_edge, s_dart_edges, side_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(side_d_width, side_d_depth), self.edges[1], 
            offset=side_len - side_dart_from_top + side_d_width / 2, right=True)
        self.edges.substitute(1, s_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, s_dart_edges[0]), pyp.Interface(self, s_dart_edges[1])))

        # Bottom dart
        bottom_d_width = (front_width - waist) * 2 / 3
        bottom_d_depth = 0.98 * (side_len - body['bust_line'])  # calculated value 0.8
        bottom_d_position = bust_point

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)
        self.edges.substitute(0, b_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

        # Take some fabric from side in the bottom 
        b_edge[-1].end[0] += (front_width - waist) / 3 

        # Take some fabric from the shoulders
        self.edges[-2].start[0] = -shoulder_width 


        # default placement
        self.translate_by([0, 30 - max_len, 0])

        # Interfaces
        self.interfaces = {
            'outside': pyp.Interface(self, [side_interface, self.edges[-3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, b_interface),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }

class BodiceFrontHalfSideAsymm(pyp.Panel):
    def __init__(self, name, body, design, shoulder_shift=2) -> None:
        super().__init__(name)

        # TODO Optimal set of body measurements?
        design = design['bodice']
        # account for ease in basic measurements
        m_bust = body['bust'] + design['ease']['v']
        m_waist = body['waist'] + design['ease']['v']

        ease = design['ease']['v'] / 4

        armscye_depth = body['armscye_depth']
        underbust_size = body['underbust'] / 4

        # sizes
        side_len = body['waist_line']
        max_len = body['waist_over_bust_line']
        bust_point = body['bust_points'] / 2

        front_frac = (body['bust'] - body['back_width']) / 2 / body['bust'] 

        self.front_width = front_frac * m_bust
        waist = front_frac * m_waist
        shoulder_width = body['sholder_w'] / 2
        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.front_width


        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-self.front_width, 0], 
            [-self.front_width, max_len + shoulder_shift], 
            [0, max_len + shoulder_shift + shoulder_incl], 
            loop=True
        )

        # Side dart
        side_dart_from_top = body['bust_line']   # TODO Should it also be adjusted? 
        side_d_depth = 0.85 * (self.front_width - bust_point)    # 0.85 NOTE: calculated value 0.8

        # DRAFT  calculated dart
        # side_edges, _, side_interface, side_dart_stitch = pyp.esf.side_with_dart_by_len(
        #     self.edges[1].start, self.edges[1].end, 
        #     target_len=side_len, depth=side_d_depth, dart_position=side_len - side_dart_from_top,   # NOTE Assuming l_section is shorter
        #     right=True, 
        #     panel=self)
        
        # # rotate to make the top strictly vertical 
        # back_to_v = copy(side_edges[-1].end)
        # side_edges.reverse().snap_to([0, 0])
        # side_edges.rotate(pyp.utils.vector_angle(
        #     np.asarray(side_edges[0].end) - np.asarray(side_edges[0].start), 
        #     [0, -1]
        # ))
        # side_edges.snap_to(back_to_v).reverse()  # back to original locaton
        # self.edges.substitute(1, side_edges)
        # self.stitching_rules.append(side_dart_stitch)

        # # TODO check the length of the waist now and adjust
        # # DEBUG
        # print('Front side w: ', self.front_width * 2)
        # print(
        #     'Front after side_dart: ', 
        #     self.edges[0].length(), waist, 
        #     side_interface.edges.length())
        # print(
        #     'Front: side diff: ', 
        #     self.front_width - self.edges[0].length(),
        #     (self.front_width - waist) / 3 * 2/3,
        #     (body['bust'] - body['waist']) / 6 * 2/3, 
        #     self.edges[0].length() - waist
        #     )

        side_d_width = max_len - side_len
        s_edge, s_dart_edges, side_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(side_d_width, side_d_depth), self.edges[1], 
            offset=side_len - side_dart_from_top + side_d_width / 2, right=True)
        self.edges.substitute(1, s_edge)
        self.stitching_rules.append(
            (pyp.Interface(self, s_dart_edges[0]), pyp.Interface(self, s_dart_edges[1])))

        # Bottom dart
        bottom_d_width = (self.front_width - waist) * 2 / 3
        # DRAFT bottom_d_width = self.edges[0].length() - waist
        if bottom_d_width > 0:  # TODO remove conditionining if this works
            bottom_d_depth = 0.98 * (side_len - body['bust_line'])  # calculated value 0.8
            bottom_d_position = bust_point

            b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
                pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
                offset=bottom_d_position, right=True)
            self.edges.substitute(0, b_edge)
            self.stitching_rules.append(
                (pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

        else:
            # maybe it's ok though..
            raise RuntimeError('BodiceFront::Error::Wrong fitting')

        # Take some fabric from side in the bottom 
        #  DRAFT b_edge[-1].end[0] += (self.front_width - waist) / 3 
        # get the proper waist size regardless of dart inclination
        b_edge[-1].end[0] = - (waist + bottom_d_width)

        # Take some fabric from the shoulders
        # DRAFT self.edges[-2].start[0] = -shoulder_width 


        # default placement
        self.translate_by([0, 30 - max_len, 0])

        # Interfaces
        self.interfaces = {
            'outside':  pyp.Interface(self, side_interface),   # side_interface,    # pyp.Interface(self, [side_interface]),  #, self.edges[-3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            'bottom': pyp.Interface(self, b_interface),
            
            # Reference to the corner for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, [self.edges[-3], self.edges[-2]]),
            'collar_corner': pyp.Interface(self, [self.edges[-2], self.edges[-1]])
        }




# DRAFT Tried proper back-front assymetry, but failed
class BodiceBackHalfAsymm0(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Make an actual fitted back
        sholder_w = body['sholder_w'] / 2
        armscye_depth = body['armscye_depth']
        
        design = design['bodice']
        length = body['waist_line']
        ease = design['ease']['v'] / 4

        # bottom dart
        bottom_d_width = (body['bust'] - body['waist']) / 6
        bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
        bottom_d_position = body['bust_points'] / 2

        # Overall measurements
        back_width = body['back_width'] / 2 + (body['bust'] - body['back_width'] - 2 * body['bust_points']) / 4 + ease

        back_fraction = back_width / (body['bust'] + ease * 4)
        waist = (body['waist'] + ease*4) * back_fraction
        waist_width = waist + bottom_d_width

        print('back: ', back_width, waist, back_fraction)  # DEBUG

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-back_width, length - armscye_depth], 
            [-sholder_w, length], 
            [0, length], 
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, [self.edges[1], self.edges[2]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[3]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[2], self.edges[3])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = b_interface

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

class BodiceBackHalf(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Make an actual fitted back
        sholder_w = body['sholder_w'] / 2
        armscye_depth = body['armscye_depth']
        
        design = design['bodice']
        length = body['waist_line']
        ease = design['ease']['v'] / 4

        # bottom dart
        bottom_d_width = (body['bust'] - body['waist']) / 6
        bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
        bottom_d_position = body['bust_points'] / 2
        
        # Overall measurements
        back_width = body['bust'] / 4 + ease
        waist = body['waist'] / 4 + ease
        waist_width = waist + bottom_d_width

        print('back: ', back_width, waist)  # DEBUG

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-back_width, length], 
            [0, length], 
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, self.edges[1]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = b_interface

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

class BodiceBackHalfFlat(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        # TODO Make an actual fitted back
        sholder_w = body['sholder_w'] / 2
        armscye_depth = body['armscye_depth']
        
        design = design['bodice']
        length = body['waist_line']
        ease = design['ease']['v'] / 4

        
        # Overall measurements
        back_width = body['bust'] / 4 + ease
        waist = body['waist'] / 4 + ease
        waist_width = back_width  # MAximally flat

        print('back: ', back_width, waist)  # DEBUG

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-back_width, length], 
            [0, length], 
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, self.edges[1]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        bottom_d_width = back_width - waist
        bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
        bottom_d_position = body['bust_points'] / 2

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = b_interface

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

class BodiceBackHalfSide(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design, shoulder_incl) -> None:
        super().__init__(name)

        # TODO Make an actual fitted back
        sholder_w = body['sholder_w'] / 2
        armscye_depth = body['armscye_depth']
        
        design = design['bodice']
        length = body['waist_line']
        ease = design['ease']['v'] / 4

        
        # Overall measurements
        back_width = body['bust'] / 4 + ease
        waist = body['waist'] / 4 + ease
        waist_width = back_width - (back_width - waist) / 3   # slight inclanation on the side

        print('back: ', back_width, waist_width)  # DEBUG

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-back_width, length - body['bust_line']],
            [-back_width, length - armscye_depth],
            [-sholder_w, length],    # Take some fabric from the shoulders
            [0, length + shoulder_incl],   # Add some fabric for the neck (inclanation of shoulders)
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, [self.edges[1], self.edges[2], self.edges[3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        bottom_d_width = (back_width - waist) * 2 / 3
        bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
        bottom_d_position = body['bust_points'] / 2

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = b_interface

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))

class BodiceBackHalfSideAsymm(pyp.Panel):
    """Panel for the front/back of upper garments"""

    def __init__(self, name, body, design) -> None:
        super().__init__(name)

        
        design = design['bodice']

        # account for ease in basic measurements
        m_bust = body['bust'] + design['ease']['v']
        m_waist = body['waist'] + design['ease']['v']

        # Overall measurements
        back_fraction = body['back_width'] / body['bust'] / 2
        
        self.back_width = back_fraction * m_bust
        waist = back_fraction * m_waist

        waist_width = self.back_width - (self.back_width - waist) / 3   # slight inclanation on the side

        print('Back side w: ', self.back_width * 2)

        # shoulder incl
        shoulder_width = body['sholder_w'] / 2   # Might be used in the sleeves? 
        armscye_depth = body['armscye_depth']   # TODO also non-symmetric
        shoulder_incl = (sh_tan:=np.tan(np.deg2rad(body['shoulder_incl']))) * self.back_width

        # side length is adjusted due to shoulder inclanation
        # for the correct sleeve fitting
        fb_diff = ((0.5 - back_fraction) - back_fraction) * body['bust']
        length = body['waist_line'] + sh_tan * fb_diff

        # Base edge loop
        self.edges = pyp.esf.from_verts(
            [0, 0], 
            [-waist_width, 0],
            [-self.back_width, body['waist_line'] - body['bust_line']],  # from the bottom
            [-self.back_width, length],   # DRAFT shoulder_width   # Take some fabric from the shoulders
            [0, length + shoulder_incl],   # Add some fabric for the neck (inclanation of shoulders)
            loop=True)
        
        self.interfaces = {
            'outside': pyp.Interface(self, [self.edges[1], self.edges[2]]),  #, self.edges[3]]),
            'inside': pyp.Interface(self, self.edges[-1]),
            'shoulder': pyp.Interface(self, self.edges[-2]),
            # Reference to the corners for sleeve and collar projections
            'shoulder_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-3], self.edges[-2])),
            'collar_corner': pyp.Interface(self, pyp.EdgeSequence(self.edges[-2], self.edges[-1]))
        }

        # Bottom dart as cutout -- for straight line
        bottom_d_width = (self.back_width - waist) * 2 / 3
        bottom_d_depth = 0.9 * (length - body['bust_line'])  # calculated value
        bottom_d_position = body['bust_points'] / 2

        b_edge, b_dart_edges, b_interface = pyp.ops.cut_into_edge(
            pyp.esf.dart_shape(bottom_d_width, bottom_d_depth), self.edges[0], 
            offset=bottom_d_position, right=True)

        self.edges.substitute(0, b_edge)
        self.interfaces['bottom'] = pyp.Interface(self, b_interface)

        # default placement
        self.translate_by([0, 30 - length, 0])

        # Stitch the dart
        self.stitching_rules.append((pyp.Interface(self, b_dart_edges[0]), pyp.Interface(self, b_dart_edges[1])))



# TODO Add design conditions -- e.g. with bottom dart or with ruffles
class FittedShirtHalf(pyp.Component):
    """Definition of a simple T-Shirt"""

    def __init__(self, name, body_opt, design_opt) -> None:
        # TODO Add params to the base classes?
        super().__init__(name)

        # Torso
        # self.ftorso = BodiceFrontHalf(f'{name}_ftorso', body_opt, design_opt).translate_by([0, 0, 20])
        self.ftorso = BodiceFrontHalfSideAsymm(f'{name}_ftorso', body_opt, design_opt, 0).translate_by([0, 0, 20])
        self.btorso = BodiceBackHalfSideAsymm(f'{name}_btorso', body_opt, design_opt).translate_by([0, 0, -20])

        print(
            'Final waist: ',
            2* (self.ftorso.interfaces['bottom'].edges.length() + self.btorso.interfaces['bottom'].edges.length()),
            self.ftorso.interfaces['bottom'].edges.length(),
            self.btorso.interfaces['bottom'].edges.length()
        )

        # Sleeves
        if design_opt['bodice']['sleeves']['v']:
            
            incl = design_opt['sleeve']['inclanation']['v']
            diff = self.ftorso.front_width - self.btorso.back_width
            front_sl = sleeves.ArmholeSquareSide('', body_opt, design_opt, shift=0, incl=incl + diff)
            back_sl = sleeves.ArmholeSquareSide('', body_opt, design_opt, shift=0, incl=incl)
            
            pyp.ops.cut_corner(front_sl, self.ftorso.interfaces['shoulder_corner'])
            pyp.ops.cut_corner(back_sl, self.btorso.interfaces['shoulder_corner'])

            # DRAFT
            # sleeve_type = getattr(sleeves, design_opt['bodice']['sleeves']['v'])
            # self.sleeve = sleeve_type(f'{name}_sl', body_opt, design_opt, shift=2)   #DRAFT 
            # if isinstance(self.sleeve, pyp.Component):
            #     # Order of edges updated after (autonorm)..
            #     _, fr_sleeve_int = pyp.ops.cut_corner(self.sleeve.interfaces[0].projecting_edges(), self.ftorso.interfaces['shoulder_corner'])
            #     _, br_sleeve_int = pyp.ops.cut_corner(self.sleeve.interfaces[1].projecting_edges(), self.btorso.interfaces['shoulder_corner'])

            #     # Sleeves are connected by new interfaces
            #     self.stitching_rules.append((self.sleeve.interfaces[0], fr_sleeve_int))
            #     self.stitching_rules.append((self.sleeve.interfaces[1], br_sleeve_int))
            # else:   # it's just an edge sequence to define sleeve shape
            #     # Simply do the projection -- no new stitches needed
            #     pyp.ops.cut_corner(self.sleeve[0], self.ftorso.interfaces['shoulder_corner'])
            #     pyp.ops.cut_corner(self.sleeve[1], self.btorso.interfaces['shoulder_corner'])

        # Collars
        # TODO collars with extra panels!
        # Front
        collar_type = getattr(collars, design_opt['bodice']['f_collar']['v'])
        f_collar = collar_type("", design_opt['bodice']['fc_depth']['v'], body_opt['neck_w'])
        pyp.ops.cut_corner(f_collar, self.ftorso.interfaces['collar_corner'])
        # Back
        collar_type = getattr(collars, design_opt['bodice']['b_collar']['v'])
        b_collar = collar_type("", design_opt['bodice']['bc_depth']['v'], body_opt['neck_w'])
        pyp.ops.cut_corner(b_collar, self.btorso.interfaces['collar_corner'])

        self.stitching_rules.append((self.ftorso.interfaces['outside'], self.btorso.interfaces['outside']))   # sides
        self.stitching_rules.append((self.ftorso.interfaces['shoulder'], self.btorso.interfaces['shoulder']))  # tops

        # DEBUG
        print('Front ls: ', self.ftorso.interfaces['outside'].edges.length(), self.ftorso.interfaces['outside'].edges.lengths())
        print('Back ls: ', self.ftorso.interfaces['outside'].edges.length(), self.btorso.interfaces['outside'].edges.lengths())

        self.interfaces = [
            self.ftorso.interfaces['inside'],  
            self.btorso.interfaces['inside'],

            # bottom
            self.ftorso.interfaces['bottom'],
            self.btorso.interfaces['bottom'],
        ]


class FittedShirt(pyp.Component):
    """Panel for the front of upper garments with darts to properly fit it to the shape"""

    def __init__(self, body, design) -> None:
        name_with_params = f"{self.__class__.__name__}"
        super().__init__(name_with_params)

        # TODO resolving names..
        self.right = FittedShirtHalf(f'right', body, design)
        self.left = FittedShirtHalf(f'left', body, design).mirror()

        self.stitching_rules.append((self.right.interfaces[0], self.left.interfaces[0]))
        self.stitching_rules.append((self.right.interfaces[1], self.left.interfaces[1]))

        self.interfaces = [   # Bottom connection
            self.right.interfaces[2],
            self.right.interfaces[3],
            self.left.interfaces[2],
            self.left.interfaces[3],
        ]
