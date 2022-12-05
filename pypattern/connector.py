from typing import Union

# Custom
from .panel import Panel
from .edge import LogicalEdge

class InterfaceInstance():
    """Single edge of a panel that can be used for connecting to"""
    def __init__(self, panel: Panel, edge_id: int, shape=None, type='full', shift=0):
        """
        Parameters:
            * panel - Panel object
            * edge_id - id of LogicalEdge in the panel that are allowed to connect to
            * shape - LogicalEdge object that describes the shape of the interface, if different from the logical edge 
                (e.g. interface shape is shorter then originial to create ruffles effect, or a cut)
            * type - relationship between interface shape and base edge
                'full': connects vertex-to-vertex, created flat full stitch or folds (depending on the length relationship)
                'portion': only part of a logical edge is getting connected (shape is shorter then the )
                'scheme': NotImplemented! (describe a scheme for a desired appearance of folds)
            * shift - how far to shift the interface along the base edge : for 'portion' interface type

            # TODO Does the shape need to be an Edge instance? -- might be needed for projection
        """

        # The base edge shape can be connected to the desired interface shape
        # * Vertex-to-vertext connection with edges of different length (creates folds on one side) 
        #   * Random folds (=ruffles)
        #   * Pleats according to a scheme, with stitching only at the edge or on the fabric itself
        # * Portion of the base edge is connected through the interface
        #   (with the shape possibly being different)

        self.panel = panel
        self.edge_id = edge_id
        self.base_edge = panel.edges[edge_id]
        self.connecting_shape = self.base_edge if shape is None else shape

        if self.connecting_shape.length > self.base_edge.length:
            raise ValueError(f'{self.__class__.__name__}::Error::interface shape cannot be longer than the base edge')

        if type == 'scheme':
            raise NotImplementedError(f'{self.__class__.__name__}::Error::pleat schemes are not implemented (yet =))')

        if type == 'portion': # create geometric edges separation in the logical edge to define the connection
            # SIM: Accomodating for Qualoth-friendly representation
            # TODO Implement
            pass

        
# DRAFT
def connect(int1:InterfaceInstance, int2:InterfaceInstance):
    """Produce a stitch that connects two interfaces

        The interfaces geometry is expected to match at this point (?)

    """
    # TODO What if connecting ids are not propagated?
    # Loop over edges again to find correspondance between logical and geometric
    # TODO OR!! Store the correspondance in the edge object when assembly is called O_o
    # In the panel or in the edge object itself O_o => Problem solved

    # TODO Multiple edges in the interface / geometric ids
    # TODO Interface containing geometric ids directly!!

    panel1 = int1.panel
    panel2 = int2.panel

    if int1.connecting_shape is not None:
        if int1.connecting_shape != int2.connecting_shape:
            # TODO Here is the place for modification of the target panel --
            # OR the panel should be modifined before this gets executed
            raise ValueError('Connecting shape does not match the target interface')
        # Else -- interface matches, it's safe to connect the edges

    return [
                {
                    'panel': panel1.name,  # corresponds to a name. 
                                            # Only one element of the first level is expected
                    'edge': panel1.edges[int1.edge_id].geometric_ids[0]  # TODO What if we only want part of the geometric ids?
                },
                {
                    'panel': panel2.name,
                    'edge': panel2.edges[int2.edge_id].geometric_ids[0]  # TODO What if we only want part of the geometric ids?
                }
            ]

# DRAFT ideas
class ConnectorOp():
    """Connects interfaces of two components and creates appropriate stitches"""
    # TODO this should produce a new component with new interface? 
    # Does it mean that every stitch produces a new component? 

    def __init__(self, c1, interface_id_1, c2, interface_id_2) -> None:
        self.c1 = c1
        self.iid1 = interface_id_1
        self.c2 = c2
        self.iid2 = interface_id_2

    def assembly(self):
        return 


