

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

    L = norm(v1 - v0)
    d1, d2 = L * location, L * (1 - location)

    depth_perp = np.sqrt((depth**2 - (width / 2)**2))
    dart_side = depth

    # DRAFT width as roots
    # print(L, d1, d2)

    # print([-d1, d1**2/(depth_perp**2 * 4) + 1/4, -d1/(4 * depth_perp**2), 1/(16*depth_perp**2)])

    # w_options = npoly.polyroots([-d1, d1**2/(depth_perp**2 * 4) + 1/4, -d1/(4 * depth_perp**2)])  #, 1/(16*depth_perp**2)])

    # print(w_options[0])  # DEBUG
    # print(w_options[1])  # DEBUG
    # # print(w_options[2])  # DEBUG

    # width = np.real(w_options)[0]  
    

    # DRAFT
    # Values as if the dart is in the middle of the edge (d1 = d2)
    # (half) of the angle of the dart tip

    # sin_poly = npoly.polyroots([- d1/depth_perp, 1, d1/depth_perp])

    # print(sin_poly)  # DEBUG

    # sin_alpha = sin_poly[(sin_poly <= 1) & (sin_poly >= -1)][0]
    # alpha = abs(np.arcsin(sin_alpha))
    

    # 

    # # dart width to satisfy the requested info
    # width = 2*np.cos(alpha)*d1 

    # DEBUG
    # Try the prev. positioning after calc width

    # coords relative to start vertex
    divisor = np.sqrt(4 * depth_perp**2 + width**2)
    p1x = 2 * d1 * depth_perp / divisor
    p1y = 2 * d1 / width / divisor

    # dart_st_point = np.array([(L - width) / 2, 0])
    # dart_st_point[1] = dart_st_point[0] * width / 2 / depth_perp
    dart_st_point_0 = np.array([p1x, p1y])
    # absolute position
    dart_st_point_0 = _rel_to_abs_coords(v0, v1, dart_st_point_0)

    # New location of the ending point to satisfy the requested dart length
    # as if it's a reflection of the 
    new_v1 = _rel_to_abs_coords(v0, v1, np.array([2 * (p1x + width/2), 0]))

    # extention of edge length
    delta_l = dart_side * width / (2 * depth_perp)

    print(width, depth_perp, dart_side, delta_l)  # DEBUG

    # Back to original v0, v1 locations
    side0, side1 = d1 + delta_l, d2 + delta_l
    
    # finding angles through the area
    alpha = abs(np.arctan(width / 2 / depth_perp))
    top_angle = np.pi - 2*alpha  # top of the triangle (v0, imaginative dart top, v1)
    long_side = np.sqrt(side0**2 + side1**2 - 2*side0*side1*np.cos(top_angle))
    sin0, sin1 = side1 * np.sin(top_angle) / long_side, side0 * np.sin(top_angle) / long_side
    angle0, angle1 = np.arcsin(sin0), np.arcsin(sin1)

    print('Triangle: ', d1, d2, long_side, side0, side1, np.rad2deg(angle0), np.rad2deg(angle1), np.rad2deg(top_angle))  # DEBUG
    print('Alpha: ', np.rad2deg(alpha))  # DEBUG

    p1x = d1 * np.cos(angle0)
    p1y = d1 * sin0
    p1 = np.array([p1x, p1y])
    print('Start point elements: ', d1, np.cos(angle0), sin0)

    # TODO these are probably not correct..
    p1 = _rel_to_abs_coords(v0, v1, p1)
    new_v1 = _rel_to_abs_coords(v0, v1, np.array([2 * (p1x + width/2), 0]))
    new_v1_1 = _rel_to_abs_coords(v0, v1, np.array([long_side, 0]))

    # print(dart_st_point, dart_st_point_0)

    # Other dart vertices
    p2x = long_side - (d2 * np.cos(angle1))
    p2y = d2 * sin1
    p2 = np.array([p2x, p2y])
    p2 = _rel_to_abs_coords(v0, v1, p2)

    p_vec = p2 - p1
    p_perp = np.array([-p_vec[1], p_vec[0]])
    p_perp = p_perp / norm(p_perp) * depth_perp

    p_tip = p1 + p_vec / 2 - p_perp

    print('Tip location: ', p_tip, p_vec, p_perp, norm(p_tip - p1))

    print('Depth: ', norm(p_tip - p1), norm(p_tip - p2))
    print('Width: ', norm(p2 - p1))
    print('Total Length requested: ', d1, d2, norm(v1 - v0))
    print('Total Length: ', norm(p1 - v0), norm(p2 - new_v1_1), norm(p1 - v0) + norm(p2 - new_v1_1))
    

    # return np.array([v0, dart_st_point, _rel_to_abs_coords(v0, v1, p_tip),  _rel_to_abs_coords(v0, v1, p2), new_v1_1])
    return np.array([v0, p1, p_tip, p2, new_v1_1])
    # return np.array([v0, dart_st_point, dart_st_point + np.array([width / 2, -depth_perp]), dart_st_point + np.array([width, 0]), new_v1, new_v1_1])



edge_side = dart(np.array([0, 0]), np.array([50, -15]), 5, 20, location=0.2)

plt.plot(edge_side[:, 0], edge_side[:, 1], marker='o')
plt.title('Dart')
plt.xlabel('x')
plt.ylabel('y')
plt.grid(True)
plt.axis('equal')
plt.show()