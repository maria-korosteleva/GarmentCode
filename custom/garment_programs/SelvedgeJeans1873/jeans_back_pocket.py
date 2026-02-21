"""
Back Pocket
Based on: Historical Tailoring Masterclasses - Drafting the Pockets and Accessories

Standalone pattern piece (not drafted on the back panel).

Dimensions:
  Height: 8" total (7" to first reference mark)
  Width:  ~6" (estimated — exact widths are in a diagram not available in text)

Seam allowances:
  Sides and bottom: 3/8"
  Top:              7/8" (accounts for double fold + denim thickness)

Grain line: centerline (pocket mouth on crossgrain).

Notes on 1873 jeans: only one pocket on the right side.
Modern jeans: one pocket on each side.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import INCH, load_measurements, _annotate_segment


# -- Drafting ----------------------------------------------------------------

def draft_jeans_back_pocket(m):
    """Draft the back pocket as a standalone piece.

    Parameters
    ----------
    m : dict
        Measurements in cm (not used — fixed dimensions).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    # All dimensions measured from point 0 (top center)
    top_half = 3.375 * INCH     # 3 3/8" each side at top
    mid_half = 2.625 * INCH     # 2 5/8" each side at 6" mark
    mid_depth = 6.0 * INCH      # vertical to the 6" mark
    total_depth = 7.0 * INCH    # vertical to the bottom point

    width = 2 * top_half        # 6 3/4" total at mouth

    # Seam allowances
    sa_side = 3 / 8 * INCH
    sa_top = 7 / 8 * INCH

    # Finished shape — origin at point 0 (top center), Y goes down
    # Using Y-up for matplotlib: top = total_depth, bottom = 0
    f_tl = np.array([top_half - top_half, total_depth])           # (0, 7)
    f_tr = np.array([top_half + top_half, total_depth])           # (6.75, 7)
    cx = top_half                                                  # center x
    f_tl = np.array([cx - top_half, total_depth])
    f_tr = np.array([cx + top_half, total_depth])
    f_ref_l = np.array([cx - mid_half, total_depth - mid_depth])  # 6" mark, left
    f_ref_r = np.array([cx + mid_half, total_depth - mid_depth])  # 6" mark, right
    f_bottom = np.array([cx, 0.0])                                # center point

    # SA outline
    sa_tl = np.array([cx - top_half - sa_side, total_depth + sa_top])
    sa_tr = np.array([cx + top_half + sa_side, total_depth + sa_top])
    sa_ref_l = np.array([cx - mid_half - sa_side, total_depth - mid_depth])
    sa_ref_r = np.array([cx + mid_half + sa_side, total_depth - mid_depth])
    sa_bottom = np.array([cx, -sa_side])

    # Grain line (center, vertical)
    grain_top = np.array([cx, total_depth * 0.85])
    grain_bottom = np.array([cx, total_depth * 0.20])

    return {
        'points': {
            'f_tl': f_tl, 'f_tr': f_tr,
            'f_ref_l': f_ref_l, 'f_ref_r': f_ref_r,
            'f_bottom': f_bottom,
            'sa_tl': sa_tl, 'sa_tr': sa_tr,
            'sa_ref_l': sa_ref_l, 'sa_ref_r': sa_ref_r,
            'sa_bottom': sa_bottom,
            'grain_top': grain_top, 'grain_bottom': grain_bottom,
        },
        'curves': {},
        'construction': {
            'ref_mark_y': np.float64(total_depth - mid_depth),
        },
        'metadata': {
            'title': 'Back Pocket',
            'width': width,
            'height': total_depth,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_back_pocket(pocket, output_path='Logs/jeans_back_pocket.svg',
                           debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in pocket['points'].items()}
    con = {k: v * s for k, v in pocket['construction'].items()}
    width_s = pocket['metadata']['width'] * s
    height_s = pocket['metadata']['height'] * s

    fig, ax = plt.subplots(1, 1, figsize=(8, 10))
    OUTLINE = dict(color='black', linewidth=1.5)
    SA_STYLE = dict(color='gray', linewidth=1, linestyle='--', alpha=0.6)

    # Finished shape (pentagon: top → right side → point → left side → top)
    f_order = ['f_tl', 'f_tr', 'f_ref_r', 'f_bottom', 'f_ref_l', 'f_tl']
    fx = [pts[k][0] for k in f_order]
    fy = [pts[k][1] for k in f_order]
    ax.plot(fx, fy, **OUTLINE)

    # SA outline
    sa_order = ['sa_tl', 'sa_tr', 'sa_ref_r', 'sa_bottom', 'sa_ref_l', 'sa_tl']
    sx = [pts[k][0] for k in sa_order]
    sy = [pts[k][1] for k in sa_order]
    ax.plot(sx, sy, **SA_STYLE)

    # Grain line arrow
    ax.annotate('', xy=pts['grain_top'], xytext=pts['grain_bottom'],
                arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))
    ax.annotate('grain', (pts['grain_top'][0], pts['grain_top'][1]),
                textcoords="offset points", xytext=(8, 0),
                fontsize=7, color='gray')

    if debug:
        # 7" reference mark
        ax.plot([0, width_s], [con['ref_mark_y'], con['ref_mark_y']],
                color='blue', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.annotate('7" ref', (width_s, con['ref_mark_y']),
                    textcoords="offset points", xytext=(4, 0),
                    fontsize=6, color='blue')

        _annotate_segment(ax, pts['f_tl'], pts['f_tr'], offset=(0, 8))
        _annotate_segment(ax, pts['f_tr'], pts['f_ref_r'], offset=(10, 0))
        _annotate_segment(ax, pts['f_ref_r'], pts['f_bottom'], offset=(10, 0))

        # SA labels
        ax.annotate('3/8" SA', (width_s / 2, pts['sa_bottom'][1]),
                    textcoords="offset points", xytext=(0, -6),
                    fontsize=6, ha='center', color='gray')
        ax.annotate('7/8" SA (top)', (width_s / 2, pts['sa_tr'][1]),
                    textcoords="offset points", xytext=(0, 6),
                    fontsize=6, ha='center', color='gray')

        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    ax.set_title(pocket['metadata']['title'])
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
    pocket = draft_jeans_back_pocket(m)
    plot_jeans_back_pocket(pocket, output_path, debug=debug, units=units)
