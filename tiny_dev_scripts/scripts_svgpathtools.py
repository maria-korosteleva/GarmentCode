"""New candidate library to work with Bezier curves, chained curves, arcs, etc. 

    also, more convenient for saving svgs of sewing patterns (probably)

"""

from svgpathtools import *
from time import sleep
import numpy as np

# First we'll load the path data from the file test.svg
# paths, attributes = svg2paths('tmp_orig_shape.svg')
paths, attributes = svg2paths('test.svg')


print(attributes)


# manually created segment
nodes = np.asarray([
    [40, 0],
    [32, -12],
    [24, 8],
    [0, 0]
])
compl = nodes[:, 0] + 1j*nodes[:, 1]


seg = CubicBezier(*compl) 


# DEBUG
print('Length: ', seg.length())
point_on_curve = seg.point(0.7)
point_on_curve = point_on_curve.real, point_on_curve.imag
print('Point: ', point_on_curve)

path = Path(seg)
paths = [path]


# Let's mark the parametric midpoint of each segment
# I say "parametric" midpoint because Bezier curves aren't 
# parameterized by arclength 
# If they're also the geometric midpoint, let's mark them
# purple and otherwise we'll mark the geometric midpoint green
min_depth = 5
error = 1e-4
dots = []
ncols = []
nradii = []
for path in paths:
    for seg in path:
        parametric_mid = seg.point(0.5)
        seg_length = seg.length()
        if seg.length(0.5)/seg.length() == 1/2:
            dots += [parametric_mid]
            ncols += ['purple']
            nradii += [1]
        else:
            t_mid = seg.ilength(seg_length/2)
            geo_mid = seg.point(t_mid)
            dots += [parametric_mid, geo_mid]
            ncols += ['red', 'green']
            nradii += [1] * 2

# In 'output2.svg' the paths will retain their original attributes
disvg(paths, nodes=dots, node_colors=ncols, node_radii=nradii, 
     attributes=attributes, filename='tmp_output2.svg')
