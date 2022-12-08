class InterfaceInstance():
    """Single edge of a panel that can be used for connecting to"""
    def __init__(self, panel, edge):
        """
        Parameters:
            * panel - Panel object
            * edge - LogicalEdge in the panel that are allowed to connect to
        """

        # The base edge shape can be connected to the desired interface shape
        # * Vertex-to-vertext connection with edges of different length (creates folds on one side) 
        #   * Random folds (=ruffles)
        #   * Pleats according to a scheme, with stitching only at the edge or on the fabric itself
        # * Portion of the base edge is connected through the interface
        #   (with the shape possibly being different)

        self.panel = panel
        self.edge = edge

        
def connect(int1:InterfaceInstance, int2:InterfaceInstance):
    """Produce a stitch that connects two interfaces

        NOTE: the interface geometry matching is not checked, and generally not required 
    """
    # TODO Multiple edges in the interface / geometric ids

    return [
                {
                    'panel': int1.panel.name,  # corresponds to a name. 
                                            # Only one element of the first level is expected
                    'edge': int1.edge.geometric_id
                },
                {
                    'panel': int2.panel.name,
                    'edge': int2.edge.geometric_id
                }
            ]


