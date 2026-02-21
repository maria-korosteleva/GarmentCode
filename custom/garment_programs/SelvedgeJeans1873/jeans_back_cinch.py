"""
Back Cinch Belt
Based on: Historical Tailoring Masterclasses - Drafting the Back Cinch Belt

A tapered belt used on 1873 and other selvedge denim jeans.

Finished shape:
  Length = 5"
  Wide end (point 0)  = 5/8" + 5/8" = 1 1/4" total
  Narrow end (point 5) = 1/2" + 1/2" = 1" total  (fits standard buckle)

Seam allowances:
  Long edges at wide end:   3/4" each side
  Long edges at narrow end: 5/8" each side
  Short ends:               1/2" each end
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import INCH, load_measurements, _annotate_segment


# -- Drafting ----------------------------------------------------------------

def draft_jeans_back_cinch(m):
    """Draft the back cinch belt (tapered strip with SA).

    Parameters
    ----------
    m : dict
        Measurements in cm (not used — fixed dimensions).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    length = 5 * INCH

    # Finished half-widths (from center line)
    wide_half = 5 / 8 * INCH
    narrow_half = 1 / 2 * INCH

    # Finished shape (centered on y = 0)
    f_tl = np.array([0.0, wide_half])
    f_bl = np.array([0.0, -wide_half])
    f_tr = np.array([length, narrow_half])
    f_br = np.array([length, -narrow_half])

    # Seam allowances
    sa_wide = 3 / 4 * INCH     # top/bottom at wide end
    sa_narrow = 5 / 8 * INCH   # top/bottom at narrow end
    sa_end = 1 / 2 * INCH      # left/right short ends

    sa_tl = np.array([-sa_end, wide_half + sa_wide])
    sa_bl = np.array([-sa_end, -(wide_half + sa_wide)])
    sa_tr = np.array([length + sa_end, narrow_half + sa_narrow])
    sa_br = np.array([length + sa_end, -(narrow_half + sa_narrow)])

    return {
        'points': {
            'f_tl': f_tl, 'f_bl': f_bl, 'f_tr': f_tr, 'f_br': f_br,
            'sa_tl': sa_tl, 'sa_bl': sa_bl, 'sa_tr': sa_tr, 'sa_br': sa_br,
        },
        'curves': {},
        'construction': {},
        'metadata': {
            'title': 'Back Cinch Belt',
            'length': length,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_back_cinch(cinch, output_path='Logs/jeans_back_cinch.svg',
                          debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in cinch['points'].items()}

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    OUTLINE = dict(color='black', linewidth=1.5)
    SA_STYLE = dict(color='gray', linewidth=1, linestyle='--', alpha=0.6)

    # Finished shape
    fx = [pts['f_tl'][0], pts['f_tr'][0], pts['f_br'][0], pts['f_bl'][0],
          pts['f_tl'][0]]
    fy = [pts['f_tl'][1], pts['f_tr'][1], pts['f_br'][1], pts['f_bl'][1],
          pts['f_tl'][1]]
    ax.plot(fx, fy, **OUTLINE)

    # SA outline
    sx = [pts['sa_tl'][0], pts['sa_tr'][0], pts['sa_br'][0], pts['sa_bl'][0],
          pts['sa_tl'][0]]
    sy = [pts['sa_tl'][1], pts['sa_tr'][1], pts['sa_br'][1], pts['sa_bl'][1],
          pts['sa_tl'][1]]
    ax.plot(sx, sy, **SA_STYLE)

    # Center line
    length_s = cinch['metadata']['length'] * s
    ax.plot([0, length_s], [0, 0],
            color='gray', linewidth=0.5, linestyle=':', alpha=0.4)

    if debug:
        for name, pt in pts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(4, 4), ha='left', fontsize=6)

        _annotate_segment(ax, pts['f_bl'], pts['f_br'], offset=(0, -10))
        _annotate_segment(ax, pts['f_tl'], pts['f_bl'], offset=(-14, 0))
        _annotate_segment(ax, pts['f_tr'], pts['f_br'], offset=(10, 0))

        ax.annotate('selvedge edge', (length_s / 2, pts['f_bl'][1]),
                    textcoords="offset points", xytext=(0, -6),
                    fontsize=6, color='gray', ha='center')

        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    ax.set_title(cinch['metadata']['title'])
    ax.set_aspect('equal')
    ax.margins(0.15)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    m = load_measurements(measurements_path)
    cinch = draft_jeans_back_cinch(m)
    plot_jeans_back_cinch(cinch, output_path, debug=debug, units=units)
