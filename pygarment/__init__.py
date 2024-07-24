"""A Python library for building sewing patterns procedurally

    # TODO Usage
    # TODO Applications/limitaitons

"""

# TODO allow direct access to mayaqltools? 
# TODO Access to pattern lib?

# Building blocks
from pygarment.component import Component
from pygarment.panel import Panel
from pygarment.edge import *
from pygarment.connector import Stitches
from pygarment.interface import Interface
from pygarment.edge_factory import EdgeSeqFactory
from pygarment.edge_factory import CircleEdgeFactory
from pygarment.edge_factory import EdgeFactory


# Operations
import pygarment.operators as ops
import pygarment.generic_utils as utils

# Parameter support
from pygarment.params import *

# Errors
from pygarment.pattern.core import EmptyPatternError

