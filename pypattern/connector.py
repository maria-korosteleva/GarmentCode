from typing import Union

# Custom
from .panel import Panel
from .edge import LogicalEdge

class InterfaceInstance():
    """Single edge of a panel that can be used for connecting to"""
    def __init__(self, panel: Panel, edge_id: int):
        """
        Parameters:
            * panel - Panel object
            * edge_id - id of LogicalEdge in the panel that are allowed to connect to
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

        
def connect(int1:InterfaceInstance, int2:InterfaceInstance):
    """Produce a stitch that connects two interfaces

        The interfaces geometry is expected to match at this point (?)

    """
    # TODO Multiple edges in the interface / geometric ids

    panel1 = int1.panel
    panel2 = int2.panel

    if int1.base_edge != int2.base_edge:
        # TODO Here is the place for modification of the target panel --
        # OR the panel should be modifined before this gets executed
        raise ValueError('Connecting edges do not match the target interface')
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


