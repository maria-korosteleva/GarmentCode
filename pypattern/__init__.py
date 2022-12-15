"""A Python library for building garments sewing patterns procedurally

    # TODO Usage
    # TODO Applications/limitaitons

"""

# Building blocks
from .component import Component
from .panel import Panel
from .edge import LogicalEdge, EdgeSequence
from .connector import Interface, Stitches
from .edge_factory import EdgeSeqFactory as esf

# Operations
import pypattern.operators as ops