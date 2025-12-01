from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation as R

import pygarment as pyg
from loguru import logger

from garment_programs.weon_circle_skirt import CircleArcPanel
from garment_programs.weon_bands import StraightBandPanel
from garment_programs.garment_enums import InterfaceName
from pattern_definitions.shirt_design import CollarDesign


# # ------ Collar shapes withough extra panels ------

def VNeckHalf(depth: float, width: float, **kwargs: Any) -> pyg.EdgeSequence:
    """Simple VNeck design.
    
    Parameters
    ----------
    depth : float
        Depth of the V-neck opening.
    width : float
        Width of the neck opening.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a V-neck collar.
    """
    edges = pyg.EdgeSequence(pyg.Edge([0, 0], [width / 2, -depth]))
    return edges

def SquareNeckHalf(depth: float, width: float, **kwargs: Any) -> pyg.EdgeSequence:
    """Square neck design.
    
    Parameters
    ----------
    depth : float
        Depth of the square neck opening.
    width : float
        Width of the neck opening.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a square neck collar.
    """
    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [0, -depth], [width / 2, -depth])
    return edges

def TrapezoidNeckHalf(
    depth: float, 
    width: float, 
    angle: float = 90, 
    verbose: bool = True, 
    **kwargs: Any
) -> pyg.EdgeSequence:
    """Trapezoid neck design.
    
    Parameters
    ----------
    depth : float
        Depth of the trapezoid neck opening.
    width : float
        Width of the neck opening.
    angle : float, optional
        Angle of the trapezoid sides in degrees. Default is 90.
    verbose : bool, optional
        Whether to print warnings. Default is True.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a trapezoid neck collar.
        Falls back to VNeckHalf if angle is invalid.
    """

    # Special case when angle = 180 (sin = 0)
    if (pyg.utils.close_enough(angle, 180, tol=1) 
            or pyg.utils.close_enough(angle, 0, tol=1)):
        # degrades into VNeck
        return VNeckHalf(depth, width)

    rad_angle = np.deg2rad(angle)

    bottom_x = -depth * np.cos(rad_angle) / np.sin(rad_angle)
    if bottom_x > width / 2:  # Invalid angle/depth/width combination resulted in invalid shape
        if verbose:
            logger.warning(f'Parameters are invalid and create overlap: {bottom_x} > {width / 2}. The collar is reverted to VNeck')

        return VNeckHalf(depth, width)

    edges = pyg.EdgeSeqFactory.from_verts([0, 0], [bottom_x, -depth], [width / 2, -depth])
    return edges

def CurvyNeckHalf(
    depth: float, 
    width: float, 
    flip: bool = False, 
    **kwargs: Any
) -> pyg.EdgeSequence:
    """Curvy collar design with curved edges.
    
    Parameters
    ----------
    depth : float
        Depth of the curvy neck opening.
    width : float
        Width of the neck opening.
    flip : bool, optional
        Whether to flip the curve direction. Default is False.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a curvy neck collar.
    """
    sign = -1 if flip else 1
    edges = pyg.EdgeSequence(pyg.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[0.4, sign * 0.3], [0.8, sign * -0.3]]))
    
    return edges

def CircleArcNeckHalf(
    depth: float, 
    width: float, 
    angle: float = 90, 
    flip: bool = False, 
    **kwargs: Any
) -> pyg.EdgeSequence:
    """Collar with a side represented by a circle arc.
    
    Parameters
    ----------
    depth : float
        Depth of the circle arc neck opening.
    width : float
        Width of the neck opening.
    angle : float, optional
        Arc angle in degrees. Default is 90.
    flip : bool, optional
        Whether to flip the arc direction. Default is False.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a circle arc neck collar.
    """
    # 1/4 of a circle
    edges = pyg.EdgeSequence(pyg.CircleEdgeFactory.from_points_angle(
        [0, 0], [width / 2,-depth], arc_angle=np.deg2rad(angle),
        right=(not flip)
    ))

    return edges


def CircleNeckHalf(depth: float, width: float, **kwargs: Any) -> pyg.EdgeSequence:
    """Collar that forms a perfect circle arc when halves are stitched.
    
    Parameters
    ----------
    depth : float
        Depth of the circle neck opening.
    width : float
        Width of the neck opening.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a circle neck collar.
    """
    # Take a full desired arc and half it!
    circle = pyg.CircleEdgeFactory.from_three_points(
        [0, 0],
        [width, 0],
        [width / 2, -depth])
    subdiv = circle.subdivide_len([0.5, 0.5])
    return pyg.EdgeSequence(subdiv[0])

def Bezier2NeckHalf(
    depth: float, 
    width: float, 
    flip: bool = False, 
    x: float = 0.5, 
    y: float = 0.3, 
    **kwargs: Any
) -> pyg.EdgeSequence:
    """2nd degree Bezier curve as neckline.
    
    Parameters
    ----------
    depth : float
        Depth of the Bezier neck opening.
    width : float
        Width of the neck opening.
    flip : bool, optional
        Whether to flip the curve direction. Default is False.
    x : float, optional
        X coordinate of the Bezier control point (normalized). Default is 0.5.
    y : float, optional
        Y coordinate of the Bezier control point (normalized). Default is 0.3.
    **kwargs
        Additional keyword arguments (unused).
    
    Returns
    -------
    pyg.EdgeSequence
        Edge sequence representing half of a Bezier neck collar.
    """
    sign = 1 if flip else -1
    edges = pyg.EdgeSequence(pyg.CurveEdge(
        [0, 0], [width / 2,-depth], 
        [[x, sign*y]]))
    
    return edges

# # ------ Collars with panels ------

class NoPanelsCollar(pyg.Component):
    """Face collar class that only forms the projected shapes.
    
    This collar component creates projection interfaces for attaching
    to the bodice but does not include physical panels. It's used for
    simple neckline designs that don't require additional fabric panels.
    
    Attributes
    ----------
    interfaces : dict
        Dictionary containing front and back projection interfaces.
    """
    
    def __init__(
        self,
        name: str,
        design: CollarDesign
    ) -> None:
        """Initialize a no-panels collar component.
        
        Parameters
        ----------
        name : str
            Name identifier for this collar component.
        design : CollarDesign
            Collar design parameters object containing front and back
            collar specifications.
        """
        super().__init__(name)

        # Front
        collar_type = globals()[design.f_collar]
        f_collar = collar_type(
            design.fc_depth,
            design.width, 
            angle=design.fc_angle, 
            flip=design.f_flip_curve,
            x=design.f_bezier_x,
            y=design.f_bezier_y,
            verbose=self.verbose
        )

        # Back
        collar_type = globals()[design.b_collar]
        b_collar = collar_type(
            design.bc_depth, 
            design.width, 
            angle=design.bc_angle,
            flip=design.b_flip_curve,
            x=design.b_bezier_x,
            y=design.b_bezier_y,
            verbose=self.verbose
        )
        
        self.interfaces = {
            InterfaceName.FRONT_PROJ: pyg.Interface(self, f_collar),
            InterfaceName.BACK_PROJ: pyg.Interface(self, b_collar)
        }
    
    def length(self) -> float:
        """Return the length of the collar.
        
        Returns
        -------
        float
            Length of the collar (0 for no-panels collar).
        """
        return 0


class Turtle(pyg.Component):
    """Turtle neck collar component with front and back panels.
    
    This collar creates a turtleneck style with front and back panels
    that form a circular opening around the neck.
    
    Attributes
    ----------
    front : StraightBandPanel
        Front panel of the turtle collar.
    back : StraightBandPanel
        Back panel of the turtle collar.
    interfaces : dict
        Dictionary containing front, back, and bottom interfaces.
    """
    
    def __init__(
        self, 
        tag: str, 
        body: dict[str, Any], 
        design: dict[str, Any]
    ) -> None:
        """Initialize a turtle neck collar component.
        
        Parameters
        ----------
        tag : str
            Tag identifier for the collar (e.g., 'right' or 'left').
        body : dict[str, Any]
            Body measurements dictionary containing height and head_l.
        design : dict[str, Any]
            Design parameters dictionary containing collar specifications.
        """
        super().__init__(f'Turtle_{tag}')

        depth = design['collar']['component']['depth']['v']

        # --Projecting shapes--
        f_collar = CircleNeckHalf(
            design['collar']['fc_depth']['v'],
            design['collar']['width']['v'])
        b_collar = CircleNeckHalf(
            design['collar']['bc_depth']['v'],
            design['collar']['width']['v'])
        
        self.interfaces = {
            InterfaceName.FRONT_PROJ: pyg.Interface(self, f_collar),
            InterfaceName.BACK_PROJ: pyg.Interface(self, b_collar)
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body['height'] - body['head_l'] + depth

        self.front = StraightBandPanel(
            f'{tag}_collar_front', length_f, depth).translate_by(
            [-length_f / 2, height_p, 10])
        self.back = StraightBandPanel(
            f'{tag}_collar_back', length_b, depth).translate_by(
            [-length_b / 2, height_p, -10])

        self.stitching_rules.append((
            self.front.interfaces[InterfaceName.RIGHT], 
            self.back.interfaces[InterfaceName.RIGHT]
        ))

        self.interfaces.update({
            InterfaceName.FRONT: self.front.interfaces[InterfaceName.LEFT],
            InterfaceName.BACK: self.back.interfaces[InterfaceName.LEFT],
            InterfaceName.BOTTOM: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.BOTTOM],
                self.back.interfaces[InterfaceName.BOTTOM]
            )
        })

    def length(self) -> float:
        """Return the length of the turtle collar.
        
        Returns
        -------
        float
            Length of the back interface edges.
        """
        return self.interfaces[InterfaceName.BACK].edges.length()


class SimpleLapelPanel(pyg.Panel):
    """A panel for the front part of a simple lapel.
    
    This panel creates the front section of a lapel collar, with
    interfaces for connecting to the collar and bodice.
    
    Attributes
    ----------
    interfaces : dict
        Dictionary containing to_collar and to_bodice interfaces.
    """
    
    def __init__(
        self, 
        name: str, 
        length: float, 
        max_depth: float
    ) -> None:
        """Initialize a simple lapel panel.
        
        Parameters
        ----------
        name : str
            Name identifier for this panel.
        length : float
            Length of the lapel panel.
        max_depth : float
            Maximum depth of the lapel opening.
        """
        super().__init__(name)

        self.edges = pyg.EdgeSeqFactory.from_verts(
            [0, 0], [max_depth, 0], [max_depth, -length]
        )

        self.edges.append(
            pyg.CurveEdge(
                self.edges[-1].end, 
                self.edges[0].start, 
                [[0.7, 0.2]]
            )
        )

        self.interfaces = {
            InterfaceName.TO_COLLAR: pyg.Interface(self, self.edges[0]),
            InterfaceName.TO_BODICE: pyg.Interface(self, self.edges[1])
        }


class SimpleLapel(pyg.Component):
    """Simple lapel collar component with front lapel panel and back panel.
    
    This collar creates a lapel-style opening with a front panel that
    can fold back and a back panel that can be straight or curved.
    
    Attributes
    ----------
    front : SimpleLapelPanel
        Front lapel panel.
    back : StraightBandPanel | CircleArcPanel
        Back panel (straight or curved depending on standing parameter).
    interfaces : dict
        Dictionary containing back and bottom interfaces.
    """
    
    def __init__(
        self, 
        tag: str, 
        body: dict[str, Any], 
        design: dict[str, Any]
    ) -> None:
        """Initialize a simple lapel collar component.
        
        Parameters
        ----------
        tag : str
            Tag identifier for the collar (e.g., 'right' or 'left').
        body : dict[str, Any]
            Body measurements dictionary containing height and head_l.
        design : dict[str, Any]
            Design parameters dictionary containing collar specifications.
        """
        super().__init__(f'Turtle_{tag}')

        depth = design['collar']['component']['depth']['v']
        standing = design['collar']['component']['lapel_standing']['v']

        # --Projecting shapes--
        # Any front one!
        collar_type = globals()[design['collar']['f_collar']['v']]
        f_collar = collar_type(
            design['collar']['fc_depth']['v'],
            design['collar']['width']['v'], 
            angle=design['collar']['fc_angle']['v'], 
            flip=design['collar']['f_flip_curve']['v'])
        
        b_collar = CircleNeckHalf(
            design['collar']['bc_depth']['v'],
            design['collar']['width']['v'])
        
        self.interfaces = {
            InterfaceName.FRONT_PROJ: pyg.Interface(self, f_collar),
            InterfaceName.BACK_PROJ: pyg.Interface(self, b_collar)
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body['height'] - body['head_l'] + depth * 2
        
        self.front = SimpleLapelPanel(
            f'{tag}_collar_front', length_f, depth).translate_by(
            [-depth * 2, height_p, 35])  # TODOLOW This should be related with the bodice panels' placement

        if standing:
            self.back = StraightBandPanel(
                f'{tag}_collar_back', length_b, depth).translate_by(
                [-length_b / 2, height_p, -10])
        else:
            # A curved back panel that follows the collar opening
            rad, angle, _ = b_collar[0].as_radius_angle()
            self.back = CircleArcPanel(
                f'{tag}_collar_back', rad, depth, angle  
            ).translate_by([-length_b, height_p, -10])
            self.back.rotate_by(R.from_euler('XYZ', [90, 45, 0], degrees=True))

        if standing:
            self.back.interfaces[InterfaceName.RIGHT].set_right_wrong(True)

        self.stitching_rules.append((
            self.front.interfaces[InterfaceName.TO_COLLAR], 
            self.back.interfaces[InterfaceName.RIGHT]
        ))

        self.interfaces.update({
            #'front': NOTE: no front interface here
            InterfaceName.BACK: self.back.interfaces[InterfaceName.LEFT],
            InterfaceName.BOTTOM: pyg.Interface.from_multiple(
                self.front.interfaces[InterfaceName.TO_BODICE].set_right_wrong(True),
                self.back.interfaces[InterfaceName.BOTTOM] if standing else self.back.interfaces[InterfaceName.TOP].set_right_wrong(True),
            )
        })

    def length(self) -> float:
        """Return the length of the simple lapel.
        
        Returns
        -------
        float
            Length of the back interface edges.
        """
        return self.interfaces[InterfaceName.BACK].edges.length()

class HoodPanel(pyg.Panel):
    """A panel for the side of a hood.
    
    This panel creates one half of a hood, with curved edges that
    form the shape of the hood when two panels are stitched together.
    
    Attributes
    ----------
    interfaces : dict
        Dictionary containing to_other_side and to_bodice interfaces.
    """
    
    def __init__(
        self, 
        name: str, 
        f_depth: float, 
        b_depth: float, 
        f_length: float, 
        b_length: float, 
        width: float, 
        in_length: float, 
        depth: float
    ) -> None:
        """Initialize a hood panel.
        
        Parameters
        ----------
        name : str
            Name identifier for this panel.
        f_depth : float
            Front depth of the hood opening.
        b_depth : float
            Back depth of the hood opening.
        f_length : float
            Front length of the hood edge.
        b_length : float
            Back length of the hood edge.
        width : float
            Width of the hood (will be halved for this panel).
        in_length : float
            Internal length of the hood.
        depth : float
            Depth of the hood panel.
        """
        super().__init__(name)

        width = width / 2  # Panel covers one half only
        length = in_length + width / 2  

        # Bottom-back
        bottom_back_in = pyg.CurveEdge(
            [-width, -b_depth], 
            [0, 0],
            [[0.3, -0.2], [0.6, 0.2]]
        )
        bottom_back = pyg.ops.curve_match_tangents(
            bottom_back_in.as_curve(), 
            [1, 0],  # Full opening is vertically aligned
            [1, 0],
            target_len=b_length,
            return_as_edge=True, 
            verbose=self.verbose
        )
        self.edges.append(bottom_back)

        # Bottom front
        bottom_front_in = pyg.CurveEdge(
            self.edges[-1].end, 
            [width, -f_depth],
            [[0.3, 0.2], [0.6, -0.2]]
        )
        bottom_front = pyg.ops.curve_match_tangents(
            bottom_front_in.as_curve(), 
            [1, 0],  # Full opening is vertically aligned
            [1, 0],
            target_len=f_length,
            return_as_edge=True,
            verbose=self.verbose
        )
        self.edges.append(bottom_front)

        # Front-top straight section 
        self.edges.append(pyg.EdgeSeqFactory.from_verts(
            self.edges[-1].end,
            [width * 1.2, length], [width * 1.2 - depth, length]
        ))
        # Back of the hood
        self.edges.append(
            pyg.CurveEdge(
                self.edges[-1].end, 
                self.edges[0].start, 
                [[0.2, -0.5]]
            )
        )

        self.interfaces = {
            InterfaceName.TO_OTHER_SIDE: pyg.Interface(self, self.edges[-2:]),
            InterfaceName.TO_BODICE: pyg.Interface(self, self.edges[0:2]).reverse()
        }

        self.rotate_by(R.from_euler('XYZ', [0, -90, 0], degrees=True))
        self.translate_by([-width, 0, 0])

class Hood2Panels(pyg.Component):
    """Hood component made from two panels.
    
    This component creates a hood by combining two HoodPanel instances
    that are stitched together to form a complete hood shape.
    
    Attributes
    ----------
    panel : HoodPanel
        The hood panel (one half, typically duplicated for full hood).
    interfaces : dict
        Dictionary containing back and bottom interfaces.
    """
    
    def __init__(
        self, 
        tag: str, 
        body: dict[str, Any], 
        design: dict[str, Any]
    ) -> None:
        """Initialize a hood component with two panels.
        
        Parameters
        ----------
        tag : str
            Tag identifier for the hood (e.g., 'right' or 'left').
        body : dict[str, Any]
            Body measurements dictionary containing height and head_l.
        design : dict[str, Any]
            Design parameters dictionary containing hood specifications.
        """
        super().__init__(f'Hood_{tag}')

        # --Projecting shapes--
        width = design['collar']['width']['v']
        f_collar = CircleNeckHalf(
            design['collar']['fc_depth']['v'],   
            design['collar']['width']['v'])
        b_collar = CircleNeckHalf(
            design['collar']['bc_depth']['v'],   
            design['collar']['width']['v'])
        
        self.interfaces = {
            InterfaceName.FRONT_PROJ: pyg.Interface(self, f_collar),
            InterfaceName.BACK_PROJ: pyg.Interface(self, b_collar)
        }

        # -- Panel --
        self.panel = HoodPanel(
            f'{tag}_hood', 
            design['collar']['fc_depth']['v'],
            design['collar']['bc_depth']['v'],
            f_length=f_collar.length(),
            b_length=b_collar.length(),
            width=width,
            in_length=body['head_l'] * design['collar']['component']['hood_length']['v'],
            depth=width / 2 * design['collar']['component']['hood_depth']['v']
        ).translate_by(
            [0, body['height'] - body['head_l'] + 10, 0])

        self.interfaces.update({
            #'front': NOTE: no front interface here
            InterfaceName.BACK: self.panel.interfaces[InterfaceName.TO_OTHER_SIDE],
            InterfaceName.BOTTOM: self.panel.interfaces[InterfaceName.TO_BODICE]
        })

    def length(self) -> float:
        """Return the length of the hood.
        
        Returns
        -------
        float
            Length of the hood panel.
        """
        return self.panel.length()

