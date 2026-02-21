"""
Jeans Waistband
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

Simple rectangular strip, one long edge on the selvedge.

Width breakdown (bottom to top):
  3/8"  — selvedge edge (bottom inside)
  1 1/2" — inside of waistband
  -------- FOLD --------
  1 1/2" — outside of waistband
  3/8"  — seam allowance (top)
  Total = 3 3/4"

Length = waist measurement + 3"–4" extra on each side.
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
    extra = 3 * INCH  # extra on each side
    length = m['waist'] + 2 * extra
    width = 3.75 * INCH

    # Section boundaries (from bottom)
    selvedge_y = 3 / 8 * INCH
    fold_y = selvedge_y + 1.5 * INCH          # bottom of fold
    outside_y = fold_y + 1.5 * INCH            # top of outside section
    # outside_y + 3/8" == width (SA at top)

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
            'selvedge_y': np.float64(selvedge_y),
            'fold_y': np.float64(fold_y),
            'outside_y': np.float64(outside_y),
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
    width_s = wb['metadata']['width'] * s

    fig, ax = plt.subplots(1, 1, figsize=(18, 4))
    OUTLINE = dict(color='black', linewidth=1.5)

    # Rectangle outline
    xs = [0, length_s, length_s, 0, 0]
    ys = [0, 0, width_s, width_s, 0]
    ax.plot(xs, ys, **OUTLINE)

    # Fold line
    ax.plot([0, length_s], [con['fold_y'], con['fold_y']],
            color='black', linewidth=1.2, linestyle='--')
    ax.annotate('FOLD', (length_s / 2, con['fold_y']),
                textcoords="offset points", xytext=(0, 4),
                fontsize=8, ha='center')

    if debug:
        # Section lines
        for y_val, label in [(con['selvedge_y'], '3/8" selvedge'),
                              (con['outside_y'], '3/8" SA above')]:
            ax.plot([0, length_s], [y_val, y_val],
                    color='blue', linewidth=0.5, linestyle=':', alpha=0.5)
            ax.annotate(label, (length_s + 0.2, y_val),
                        fontsize=6, color='blue', va='center')

        # Section labels
        ax.annotate('selvedge', (length_s / 2, con['selvedge_y'] / 2),
                    fontsize=7, ha='center', va='center', color='gray')
        ax.annotate('inside (1 1/2")',
                    (length_s / 2, (con['selvedge_y'] + con['fold_y']) / 2),
                    fontsize=7, ha='center', va='center', color='gray')
        ax.annotate('outside (1 1/2")',
                    (length_s / 2, (con['fold_y'] + con['outside_y']) / 2),
                    fontsize=7, ha='center', va='center', color='gray')
        ax.annotate('SA', (length_s / 2, (con['outside_y'] + width_s) / 2),
                    fontsize=7, ha='center', va='center', color='gray')

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
