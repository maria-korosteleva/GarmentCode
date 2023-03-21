"""A Python library for building sewing patterns procedurally

    # TODO Usage
    # TODO Applications/limitaitons

"""

# Building blocks
from .component import Component
from .panel import Panel
from .edge import Edge, EdgeSequence, CircleEdge
from .connector import Stitches
from .interface import Interface
from .edge_factory import EdgeSeqFactory as esf

# Operations
import pypattern.operators as ops
import pypattern.generic_utils as utils

