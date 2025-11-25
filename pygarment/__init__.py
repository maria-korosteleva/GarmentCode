"""
    A Python library for building parametric sewing pattern programs
"""

# Configure logging automatically when package is imported
try:
    import log_config  # noqa: F401
except ImportError:
    # If log_config is not available, use default loguru configuration
    pass

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
import pygarment.garmentcode.utils as utils

# Parameter support
from pygarment.garmentcode.params import BodyParametrizationBase, DesignSampler

# Errors
from pygarment.pattern.core import EmptyPatternError

