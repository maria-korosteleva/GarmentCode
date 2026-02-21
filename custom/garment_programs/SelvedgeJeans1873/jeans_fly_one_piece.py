"""
One-Piece Fly (Modern / Post-1877)
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

The one-piece fly is a rectangle, folded in half.

Layout (left to right):
  1/2"   — seam allowance
  1 3/4" — front half
  -------- FOLD --------
  1 3/4" — back half
  1/2"   — seam allowance
  Total width = 4 1/2"

Length = 2 × fly_extension + 2"
  where fly_extension is the rise curve length from the front panel.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _curve_length, _annotate_segment,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_fly_one_piece(m, front):
    """Draft the one-piece (modern) fly as a rectangle.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of ``draft_jeans_front(m)``.

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fly_extension = _curve_length(front['curves']['rise'])
    length = 2 * fly_extension + 2 * INCH
    width = 4.5 * INCH

    sa = 0.5 * INCH             # seam allowance on each side
    front_half = 1.75 * INCH    # front half width
    fold_x = sa + front_half    # fold line position

    bl = np.array([0.0, 0.0])
    br = np.array([width, 0.0])
    tr = np.array([width, length])
    tl = np.array([0.0, length])

    return {
        'points': {
            'bl': bl, 'br': br, 'tr': tr, 'tl': tl,
        },
        'curves': {},
        'construction': {
            'fold_x': np.float64(fold_x),
            'sa_left_x': np.float64(sa),
            'sa_right_x': np.float64(width - sa),
        },
        'metadata': {
            'title': 'One-Piece Fly',
            'length': length,
            'width': width,
            'fly_extension': fly_extension,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_fly_one_piece(fly, output_path='Logs/jeans_fly_one_piece.svg',
                          debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in fly['points'].items()}
    con = {k: v * s for k, v in fly['construction'].items()}
    length_s = fly['metadata']['length'] * s
    width_s = fly['metadata']['width'] * s

    fig, ax = plt.subplots(1, 1, figsize=(6, 14))
    OUTLINE = dict(color='black', linewidth=1.5)

    # Rectangle
    xs = [0, width_s, width_s, 0, 0]
    ys = [0, 0, length_s, length_s, 0]
    ax.plot(xs, ys, **OUTLINE)

    # Fold line
    ax.plot([con['fold_x'], con['fold_x']], [0, length_s],
            color='black', linewidth=1.2, linestyle='--')
    ax.annotate('FOLD', (con['fold_x'], length_s / 2),
                textcoords="offset points", xytext=(4, 0),
                fontsize=8, ha='left', rotation=90)

    if debug:
        # Seam allowance lines
        ax.plot([con['sa_left_x'], con['sa_left_x']], [0, length_s],
                color='blue', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.plot([con['sa_right_x'], con['sa_right_x']], [0, length_s],
                color='blue', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.annotate('SA', (con['sa_left_x'] / 2, length_s / 2),
                    fontsize=6, ha='center', color='blue', rotation=90)
        ax.annotate('SA', ((con['sa_right_x'] + width_s) / 2, length_s / 2),
                    fontsize=6, ha='center', color='blue', rotation=90)

        # Section labels
        ax.annotate('front',
                    ((con['sa_left_x'] + con['fold_x']) / 2, length_s / 2),
                    fontsize=7, ha='center', va='center', color='gray',
                    rotation=90)
        ax.annotate('back',
                    ((con['fold_x'] + con['sa_right_x']) / 2, length_s / 2),
                    fontsize=7, ha='center', va='center', color='gray',
                    rotation=90)

        _annotate_segment(ax, pts['bl'], pts['br'], offset=(0, -10))
        _annotate_segment(ax, pts['br'], pts['tr'], offset=(10, 0))

        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    ax.set_title(fly['metadata']['title'])
    ax.set_aspect('equal')
    ax.margins(0.1)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    fly = draft_jeans_fly_one_piece(m, front)
    plot_jeans_fly_one_piece(fly, output_path, debug=debug, units=units)
