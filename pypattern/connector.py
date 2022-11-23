# Custom
from .edge import Edge
from .component import Component

class ConnectorEdge():
    """Edge that describes connecting interface of a component. 
        
        Differs from the generic edge by describing how it relates to the geometric edge of a panel

        Component interfaces do not necessarily have to follow the shape of panel edges, 
        which allows to create flounces, pleats and partial connections

    """

    def __init__(self, connector_shape: Edge, parent_edge: Edge) -> None:
        """ Create connector edge
        Parameters:
            * connector_edge: describes the shape of the interface edge 
            * parent_edge: the geometric edge of the panel that connector attaches too
        """
        # TODO Connector shorter than parent -- connection location
        # TODO Connector follows the parent length with different shape
        # TODO what space is connector defined in?
        self.edge = connector_shape
        self.parent = parent_edge

    def connect_to(self, connector):
        """Connect current connector with connector of another panel"""

        # TODO there is probably a more abstract object that should do it
        self.connecting = connector
        connector.connect_to(self)


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

# DRAFT
def stitch(panel1_raw, int_id1, panel2_raw, int_id2):
    name_1 = list(panel1_raw.keys())[0]
    name_2 = list(panel2_raw.keys())[0]
    return [
                {
                    'panel': name_1,  # corresponds to a name. 
                                             # Only one element of the first level is expected
                    'edge': panel1_raw[name_1]['connecting_ids'][int_id1]
                },
                {
                    'panel': name_2,
                    'edge': panel2_raw[name_2]['connecting_ids'][int_id2]
                }
            ]

