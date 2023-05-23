"""A decorative shapes"""

import numpy as np
import matplotlib.pyplot as plt  # DEBUG

# Custom
import pypattern as pyp

def sample(curve, length, stride, n_points, shift=0):

    

    ts = [(shift + i*stride) / length for i in range(n_points)]
    verts = [curve.point(t) for t in ts]

    for i in range(len(verts)):
        verts[i] = [verts[i].real, verts[i].imag]

    # DEBUG
    print(ts)
    print(verts)

    return verts

def Sun(width, depth, n_rays=8, d_rays=5):
    """Sun-like mark"""

    # Outer arc
    out_arc = pyp.CircleEdge.from_three_points(
        [0, 0], [width, 0], [width/2, depth]
    )
    in_arc = pyp.CircleEdge.from_three_points(
        [d_rays, 0], [width - d_rays, 0], [width/2, depth - d_rays]
    )
    out_curve = out_arc.as_curve()
    in_curve = in_arc.as_curve()

    # Sample with stride
    out_stride = out_arc.length() / n_rays
    in_stride = in_arc.length() / n_rays
    
    out_verts = sample(out_curve, out_arc.length(), out_stride, n_rays, out_stride / 2)
    in_verts = sample(in_curve, in_arc.length(), in_stride, n_rays + 1, 0)

    # Mix the vertices in the right order
    verts = out_verts
    for i in range(len(in_verts)):
        verts.insert(i*2, in_verts[i])

    # DEBUG
    plot(verts)
    plt.title('Sunshine')
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()
    
    return pyp.esf.from_verts(verts=verts)


# DEBUG
def plot(points, tag='Shape'):
    
    points = np.asarray(points)
    plt.plot(points[:, 0], points[:, 1], label=tag + " Curve")
    plt.scatter(points[:, 0], points[:, 1], label=tag + " Curve")


if __name__ == '__main__':
    Sun(30, 15)