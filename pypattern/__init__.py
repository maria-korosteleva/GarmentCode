"""A Python library for building sewing patterns
"""

# Building blocks
from .component import Component
from .panel import Panel
from .edge import *
from .connector import Stitches
from .interface import Interface
from .edge_factory import EdgeSeqFactory as esf

# Operations
import pypattern.operators as ops
import pypattern.generic_utils as utils
import pypattern.flags as flags

# Parameter support
from .params import *

