"""A Python library for building sewing patterns procedurally

    # TODO Usage
    # TODO Applications/limitaitons

"""

# Building blocks
from pygarment.garmentcode.component import Component
from pygarment.garmentcode.panel import Panel
from pygarment.garmentcode.edge import Edge, CircleEdge, CurveEdge, EdgeSequence
from pygarment.garmentcode.connector import Stitches
from pygarment.garmentcode.interface import Interface
from pygarment.garmentcode.edge_factory import EdgeSeqFactory
from pygarment.garmentcode.edge_factory import CircleEdgeFactory
from pygarment.garmentcode.edge_factory import EdgeFactory
from pygarment.garmentcode.edge_factory import CurveEdgeFactory


# Operations
import pygarment.garmentcode.operators as ops
import pygarment.garmentcode.generic_utils as utils

# Parameter support
from pygarment.garmentcode.params import BodyParametrizationBase, DesignSampler

# Errors
from pygarment.pattern.core import EmptyPatternError

