"""Exception classes for box mesh generation."""


class PatternLoadingError(BaseException):
    """Raised when a pattern cannot be loaded correctly to 3D."""

    pass


class MultiStitchingError(BaseException):
    """Raised when a panel edge is stitched together with more than one other edge."""

    pass


class StitchingError(BaseException):
    """Raised when one cannot find successful stitching sequence."""

    pass


class DegenerateTrianglesError(BaseException):
    """Raised when panel meshing produces degenerate triangles."""

    pass


class NormError(BaseException):
    """Raised when a panel norm is NAN."""

    pass

