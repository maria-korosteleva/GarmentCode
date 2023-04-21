import numpy as np
import matplotlib.pyplot as plt
from svgpathtools import QuadraticBezier, CubicBezier
import svgpathtools as svgpath

from pypattern.generic_utils import c_to_list

def plot_bezier_curve(curve, control_points, bounding_points, extreme_points, title):
    t_values = np.linspace(0, 1, num=1000)
    curve_points = np.array([c_to_list(curve.point(t)) for t in t_values])

    plt.plot(curve_points[:, 0], curve_points[:, 1], label="Bezier Curve")
    # plt.scatter([p.real for p in extreme_points], [p.imag for p in extreme_points], color='red', label="Extreme Points")
    plt.scatter(extreme_points[:, 0], extreme_points[:, 1], color='red', label="Extreme Points")
    plt.scatter(control_points[:, 0], control_points[:, 1], color='blue', label="Control Points")
    plt.scatter(bounding_points[:, 0], bounding_points[:, 1], color='yellow', label="Control Points")
    plt.title(title)
    plt.legend()
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()



# cubic_control = np.array([[0, 0], [0.2, 0.3], [0.4, -0.7], [1, 0]])
# params = cubic_control[:, 0] + 1j*cubic_control[:, 1]
# curve = CubicBezier(*params)


control = np.array([[0, 0], [0.4, 0.2], [1, 0]])

params = control[:, 0] + 1j*control[:, 1]
curve = QuadraticBezier(*params)
xmin, xmax, ymin, ymax = curve.bbox()

print('Bounding Box ', xmin, xmax, ymin, ymax)
bounding_points = np.array([[xmin, ymin], [xmax, ymin], [xmin, ymax], [xmax, ymax]])


# Extrema
# Variation of https://github.com/mathandy/svgpathtools/blob/5c73056420386753890712170da602493aad1860/svgpathtools/bezier.py#L197
poly = svgpath.bezier2polynomial(curve, return_poly1d=True)
y = svgpath.imag(poly)
dy = y.deriv()
y_extremizers = [0, 1] + svgpath.polyroots(dy, realroots=True,
                                condition=lambda r: 0 < r < 1)

extreme_points = np.array([c_to_list(curve.point(t)) for t in y_extremizers])

plot_bezier_curve(curve, control, bounding_points, extreme_points, 'Bounding Box')


# => Linearize
# => Stable norm evaluation!!