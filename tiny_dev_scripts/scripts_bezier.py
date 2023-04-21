import numpy as np
from scipy.integrate import fixed_quad

import bezier  # YAY!!!
import matplotlib.pyplot as plt


# Length of a cubic Bezier curve
# Derivatives are here
# https://en.wikipedia.org/wiki/B%C3%A9zier_curve

# Define the cubic Bezier curve
P0 = np.array([40, 0])
P1 = np.array([32, -12])
P2 = np.array([24, 8])
P3 = np.array([0, 0])

# Define the integrand
def integrand(t):
    # Compute the derivative of the Bezier curve at t

    t = t[0]

    derivative = 3*(1-t)**2*(P1-P0) + 6*(1-t)*t*(P2-P1) + 3*t**2*(P3-P2)
    derivative_mag = np.linalg.norm(derivative)
    return derivative_mag

# Compute the length of the curve using Gaussian quadrature
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.fixed_quad.html
length, _ = fixed_quad(integrand, 0, 1, n=5)

print("Length of Bezier curve (manual):", length)


# With library
nodes = np.asarray([
    [40, 0],
    [32, -12],
    [24, 8],
    [0, 0]
])
nodes = nodes.transpose()
nodes = np.asfortranarray(nodes)
curve = bezier.Curve(nodes, degree=3)

print(curve.implicitize())
print(curve.to_symbolic())
print('Length: ', curve.length)

point_on_curve = curve.evaluate(0.7)
print('Point: ', point_on_curve)

print('Inverse: ', curve.locate(point_on_curve))

subset = curve.specialize(0.1, 0.6)
print('subset:', subset)
print('subset length: ', subset.length)
print(subset.nodes)

# Intersect point(s) with a straight line
nodes1 = np.asfortranarray([
    [0.0, 0.5, 1.0],
    [0.0, 1.0, 0.0],
])
curve1 = bezier.Curve(nodes1, degree=2)
nodes2 = np.asfortranarray([
    [0.0  , 1.0  ],
    [0.375, 0.375],
])
curve2 = bezier.Curve(nodes2, degree=1)
intersections = curve1.intersect(curve2)

s_vals = np.asfortranarray(intersections[0, :])
int_points = curve1.evaluate_multi(s_vals)

ax1 = curve1.plot(40)
_ = curve2.plot(40, ax=ax1)

lines = ax1.plot(
    int_points[0, :], int_points[1, :],
    marker="o", linestyle="None", color="black")

plt.show()


# Intersect points with a curve

nodes1 = np.asfortranarray([
    [0.0, 0.5, 1.0],
    [0.0, 1.0, 0.0],
])
curve1 = bezier.Curve(nodes1, degree=2)
nodes2 = np.asfortranarray([
    [1.125,  0.625, 0.125],
    [0.5  , -0.5  , 0.5  ],
])
curve2 = bezier.Curve(nodes2, degree=2)
intersections = curve1.intersect(curve2)

sq31 = np.sqrt(31.0)
expected_ints = np.asfortranarray([
    [9 - sq31, 9 + sq31],
    [9 + sq31, 9 - sq31],
]) / 16.0

max_err = np.max(np.abs(intersections - expected_ints))

print('Intersection error (param): ', max_err)

s_vals = np.asfortranarray(intersections[0, :])
points = curve1.evaluate_multi(s_vals)

expected_pts = np.asfortranarray([
    [36 - 4 * sq31, 36 + 4 * sq31],
    [    16 + sq31, 16 - sq31    ],
]) / 64.0
max_err = np.max(np.abs(points - expected_pts))
print('Intersection error (points): ', max_err)


ax1 = curve1.plot(40)
_ = curve2.plot(40, ax=ax1)

lines = ax1.plot(
    points[0, :], points[1, :],
    marker="o", linestyle="None", color="black")
lines = ax1.plot(
    expected_pts[0, :], expected_pts[1, :],
    marker="o", linestyle="None", color="red")

plt.show()