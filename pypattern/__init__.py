"""A Python library for building sewing patterns procedurally

    # TODO Usage
    # TODO Applications/limitaitons

"""

# Building blocks
from pypattern.component import Component
from pypattern.panel import Panel
from pypattern.edge import *
from pypattern.connector import Stitches
from pypattern.interface import Interface
from pypattern.edge_factory import EdgeSeqFactory
from pypattern.edge_factory import CircleEdgeFactory
from pypattern.edge_factory import EdgeFactory


# Operations
import pypattern.operators as ops
import pypattern.generic_utils as utils

# Parameter support
from pypattern.params import *

