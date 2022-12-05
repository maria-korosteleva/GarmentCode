import numpy as np
from numpy.linalg import norm

# Custom
from .base import BaseComponent

class LogicalEdge(BaseComponent):
    """Edge -- an individual segement of a panel border connecting two panel vertices, 
    where the sharp change of direction occures, the basic building block of panels

    Edges are defined on 2D coordinate system with Start vertex as an origin and (End-Start) as Ox axis

    Logical edges may be constructred from multiple geometric edges (e.g., if an edge is cut with a dart), 
    and contain internal vertices at assembly time, and be defined as smooth curves.
    
    """

    def __init__(self, start=[0,0], end=[0,0], ruffle_rate=1) -> None:
        """ Simple edge inititalization.
        Parameters: 
            * start, end: from/to vertcies that the edge connectes, describing the _interface_ of an edge
            * ruffle_rate: elongate the edge at assembly time by this rate. This parameter creates ruffles on stitches

            # TODO Add support for fold schemes to allow guided folds at the edge (e.g. pleats)
        """
        super().__init__('edge')

        # TODO add curvatures
        # TODO add parameters
        # TODO add documentation

        self.start = start  # NOTE: careful with references to vertex objects
        self.end = end

        nstart = np.asarray(start)
        nend = np.asarray(end)

        # Remember the "interface" length -- before ruffles application
        self.int_length = norm(nend - nstart)

        if ruffle_rate < 1:
            raise ValueError(f'{self.__class__.__name__}::Error::Ruffle rate cannot be smaller than 1')
        if ruffle_rate > 1:
            self._ruffle(ruffle_rate)

        # ID w.r.t. other edges in a super-panel
        # Filled out at the panel assembly time
        self.geometric_id = 0

    def __eq__(self, __o: object) -> bool:
        """Special implementation of comparison: same edges == edges are allowed to be connected
            Edges are the same if their interface representation (no ruffles) is the same up to rigid transformation (rotation/translation)
                => vertices do not have to be on the same locations
        """
        if not isinstance(__o, LogicalEdge):
            return False

        # Base length is the same
        if self.int_length != __o.int_length:
            return False
            
        # TODO Curvature is the same
        # TODO special features are matching 

        # TODO Mapping geometric ids to vertices pairs??
        # I need a method to get geometric ids \ for a given subsection of the edge
        # Actually.. Edge interface definitions????

        return True

    # Actions
    def _ruffle(self, ruffle_rate):
        """Modify edge s.t. it ruffles on stitching"""

        # Calc amount of extention to match the ruffle rate
        nstart, nend = np.array(self.start), np.array(self.end)
        mid_point = (nstart + nend) / 2

        # Assuming the edge is straight 
        # TODO account for curvatures
        start_shift = (nstart - mid_point) * (ruffle_rate - 1)
        end_shift = (nend - mid_point) * (ruffle_rate - 1)

        # UPD the vertices location
        self.start[0] += start_shift[0]
        self.start[1] += start_shift[1]

        self.end[0] += end_shift[0]
        self.end[1] += end_shift[1]

        # DEBUG
        print(
            f'{self.__class__.__name__}::Notice::Edge extended from {self.int_length:.2f}'
            f' to {norm(nstart + start_shift - (nend + end_shift)):.2f} to add ruffles')

    def flip(self):
        """Flip the direction of the edge"""
        self.start, self.end = self.end, self.start

        # TODO flip curvatures
        
    # Assembly into serializable object
    def assembly(self):
        """Returns the dict-based representation of edges"""

        # TODO simply use the edge sequence? Without defining the vertices??
        return [self.start, self.end], {"endpoints": [0, 1]}