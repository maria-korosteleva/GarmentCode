"""
Jeans Waistband
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

Simple rectangular strip, one long edge on the selvedge.
No fold — the piece is cut as a single layer.

Width breakdown (bottom to top):
  3/8"  — selvedge edge (bottom)
  1 1/2" — inside of waistband
  1 1/2" — outside of waistband
  3/8"  — seam allowance (top)
  Total = 3 3/4"

Length = waist measurement + 3"–4" extra on each side (for turning under ends
and room for error).
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import INCH, load_measurements, _annotate_segment


# -- Drafting ----------------------------------------------------------------

def draft_jeans_waistband(m):
    """Draft the waistband as a rectangular strip.

    Parameters
    ----------
    m : dict
        Measurements in cm.

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    extra = 3 * INCH   # extra on each side (3" min per instructions)
    length = m['waist'] + 2 * extra
    width = 3.75 * INCH

    # Section boundaries (bottom → top)
    selvedge_y = 3/8 * INCH          # selvedge edge line
    center_y   = selvedge_y + 1.5 * INCH   # inside / outside division
    sa_y       = center_y   + 1.5 * INCH   # seam-allowance line (3/8" from top)
    # sa_y + 3/8" == width  ✓

    # Corner points
    bl = np.array([0.0, 0.0])
    br = np.array([length, 0.0])
    tr = np.array([length, width])
    tl = np.array([0.0, width])

    return {
        'points': {
            'bl': bl, 'br': br, 'tr': tr, 'tl': tl,
        },
        'curves': {},
        'construction': {
            'selvedge_y':  np.float64(selvedge_y),
            'center_y':    np.float64(center_y),
            'sa_y':        np.float64(sa_y),
            'extra':       np.float64(extra),
        },
        'metadata': {
            'title': 'Jeans Waistband',
            'length': length,
            'width': width,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_waistband(wb, output_path='Logs/jeans_waistband.svg',
                         debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in wb['points'].items()}
    con = {k: v * s for k, v in wb['construction'].items()}
    length_s = wb['metadata']['length'] * s
    width_s  = wb['metadata']['width'] * s

    fig, ax = plt.subplots(1, 1, figsize=(18, 4))
    OUTLINE = dict(color='black', linewidth=1.5)
    REF     = dict(color='dimgray', linewidth=0.8, linestyle='--', alpha=0.6)

    # --- Rectangle outline ---
    xs = [0, length_s, length_s, 0, 0]
    ys = [0, 0, width_s, width_s, 0]
    ax.plot(xs, ys, **OUTLINE)

    # --- Always-visible reference lines ---

    # Selvedge line (3/8" from bottom)
    ax.plot([0, length_s], [con['selvedge_y'], con['selvedge_y']], **REF)
    ax.annotate('selvedge edge  3/8"',
                (length_s / 2, con['selvedge_y'] / 2),
                fontsize=7, ha='center', va='center', color='dimgray')

    # Inside / outside division (center of visible waistband)
    ax.plot([0, length_s], [con['center_y'], con['center_y']], **REF)
    ax.annotate('inside  1½"',
                (length_s / 2, (con['selvedge_y'] + con['center_y']) / 2),
                fontsize=7, ha='center', va='center', color='dimgray')
    ax.annotate('outside  1½"',
                (length_s / 2, (con['center_y'] + con['sa_y']) / 2),
                fontsize=7, ha='center', va='center', color='dimgray')

    # SA line (3/8" from top) — "extra 3/4"" region made visible
    ax.plot([0, length_s], [con['sa_y'], con['sa_y']], **REF)
    ax.annotate('SA  3/8"',
                (length_s / 2, (con['sa_y'] + width_s) / 2),
                fontsize=7, ha='center', va='center', color='dimgray')

    # --- End extent marks — show where the waist measurement runs ---
    extra_s = con['extra']
    for x in [extra_s, length_s - extra_s]:
        ax.plot([x, x], [0, width_s],
                color='steelblue', linewidth=0.9, linestyle='--', alpha=0.7)
    ax.annotate('← waist →',
                (length_s / 2, width_s + 0.15 * s),
                fontsize=7, ha='center', va='bottom', color='steelblue')

    if debug:
        _annotate_segment(ax, pts['bl'], pts['br'], offset=(0, -10))
        _annotate_segment(ax, pts['tl'], pts['bl'], offset=(-14, 0))
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    ax.set_title(wb['metadata']['title'])
    ax.set_aspect('equal')
    ax.margins(0.05)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    m = load_measurements(measurements_path)
    wb = draft_jeans_waistband(m)
    plot_jeans_waistband(wb, output_path, debug=debug, units=units)
