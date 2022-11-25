# Custom
from .panel import Panel
from .edge import LogicalEdge

class InterfaceInstance():
    """Single edge of a panel that can be used for connecting to"""
    def __init__(self, panel: Panel, edge_id: int) -> None:
        self.panel = panel
        self.edge_id = edge_id

        
# DRAFT
def connect(int1:InterfaceInstance, int2:InterfaceInstance):
    # TODO What if connecting ids are not propagated?
    # Loop over edges again to find correspondance between logical and geometric
    # TODO OR!! Store the correspondance in the edge object when assembly is called O_o
    # In the panel or in the edge object itself O_o => Problem solved

    # TODO Multiple edges in the interface / geometric ids
    # TODO Interface containing geometric ids directly!!

    panel1 = int1.panel
    panel2 = int2.panel
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


