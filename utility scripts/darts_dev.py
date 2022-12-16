

import numpy as np
from numpy.linalg import norm
from numpy.polynomial import polynomial as npoly
import matplotlib.pyplot as plt


def _rel_to_abs_coords(start, end, vrel):
        """Convert coordinates specified relative to vector v2 - v1 to world coords"""
        start, end, vrel = np.asarray(start), np.asarray(end), np.asarray(vrel)
        vec = end - start
        vec = vec / norm(vec)
        vec_perp = np.array([-vec[1], vec[0]])
        
        new_start = start + vrel[0] * vec
        new_point = new_start + vrel[1] * vec_perp

        return new_point 

def dart(v0, v1, width, depth, location=0.5):

    # TODO Depth to be the length of the side rather then the norm to the dart

    L = norm(v1 - v0)
    d1, d2 = L * location, L * (1 - location)

    # DRAFT width as roots
    # print(L, d1, d2)

    # print([-d1, d1**2/(depth**2 * 4) + 1/4, -d1/(4 * depth**2), 1/(16*depth**2)])

    # w_options = npoly.polyroots([-d1, d1**2/(depth**2 * 4) + 1/4, -d1/(4 * depth**2)])  #, 1/(16*depth**2)])

    # print(w_options[0])  # DEBUG
    # print(w_options[1])  # DEBUG
    # # print(w_options[2])  # DEBUG

    # width = np.real(w_options)[0]  
    

    # DRAFT
    # Values as if the dart is in the middle of the edge (d1 = d2)
    # (half) of the angle of the dart tip
    # sin_poly = npoly.polyroots([- d1/depth, 1, d1/depth])

    # print(sin_poly)  # DEBUG

    # sin_alpha = sin_poly[(sin_poly <= 1) & (sin_poly >= -1)][0]
    # alpha = abs(np.arcsin(sin_alpha))
    

    # print(np.rad2deg(alpha),  np.rad2deg(top_angle))  # DEBUG

    # # dart width to satisfy the requested info
    # width = 2*np.cos(alpha)*d1 

    # DEBUG
    # Try the prev. positioning after calc width

    # coords relative to start vertex
    divisor = np.sqrt(4 * depth**2 + width**2)
    p1x = 2 * d1 * depth / divisor
    p1y = 2 * d1 / width / divisor

    # dart_st_point = np.array([(L - width) / 2, 0])
    # dart_st_point[1] = dart_st_point[0] * width / 2 / depth
    dart_st_point = np.array([p1x, p1y])
    # absolute position
    dart_st_point = _rel_to_abs_coords(v0, v1, dart_st_point)


    # extention of edge length
    dart_side = np.sqrt(depth**2 + width**2/4)
    
    delta_l = dart_side * width / (2 * depth)

    print(width, dart_side, delta_l)  # DEBUG

    # Back to original v0, v1 locations
    side0, side1 = d1 + delta_l, d2 + delta_l
    
    # finding angles through the area
    alpha = abs(np.arccos(width / 2 / depth))
    top_angle = np.pi - 2*alpha  # top of the triangle (v0, imaginative dart top, v1)
    sin0, sin1 = side1 * np.sin(top_angle) / L, side0 * np.sin(top_angle) / L

    print(d1, d2, L, side0, side1, sin0, sin1)  # DEBUG
    

    return np.array([v0, dart_st_point, dart_st_point + np.array([width / 2, -depth]), dart_st_point + np.array([width, 0]), v1])



edge_side = dart(np.array([0, 0]), np.array([50, 0]), 5, 10)

plt.plot(edge_side[:, 0], edge_side[:, 1], marker='o')
plt.title('Dart')
plt.xlabel('x')
plt.ylabel('y')
plt.grid(True)
plt.show()