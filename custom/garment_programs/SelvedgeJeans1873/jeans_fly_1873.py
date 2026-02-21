"""
1873 Jeans Fly (Two-Piece, cut on fold)
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

Drafted from the completed front panel.  The fly piece is symmetric about
a fold line.  Only the half-piece is drawn; cut on fold to produce the full
fly.

Steps:
1. Draw a line parallel to the front fly line, 1 3/4" from the seam line.
2. Draw a curve at the bottom of the fly extension.
3. Copy outline to fresh sheet.
4. Add ~1" inlay at the top edge.
5. Cut on fold.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _curve_length, _annotate_segment,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_fly_1873(m, front):
    """Draft the 1873 two-piece fly (half-piece, cut on fold).

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
    # Fly height = length of the front rise curve (1' → 7')
    fly_height = _curve_length(front['curves']['rise'])
    half_width = 1.75 * INCH   # 1 3/4" from seam line
    inlay = 1.0 * INCH         # extra at top to be trimmed

    # Standalone coordinate system:
    #   origin at bottom of fold line, Y up, X to the right
    fold_bottom = np.array([0.0, 0.0])
    fold_top = np.array([0.0, fly_height + inlay])
    outer_top = np.array([half_width, fly_height + inlay])
    # The outer edge runs straight down to where the bottom curve begins
    curve_start = np.array([half_width, fly_height * 0.15])

    # Bottom curve from curve_start back to the fold line
    curve_bottom = _bezier_cubic(
        curve_start,
        np.array([half_width, 0.0]),
        np.array([half_width * 0.3, 0.0]),
        fold_bottom,
    )

    return {
        'points': {
            'fold_bottom': fold_bottom,
            'fold_top': fold_top,
            'outer_top': outer_top,
            'curve_start': curve_start,
        },
        'curves': {
            'bottom': curve_bottom,
        },
        'construction': {
            'inlay_y': np.float64(fly_height),
        },
        'metadata': {
            'title': '1873 Jeans Fly (Two-Piece, cut on fold)',
            'fly_height': fly_height,
            'half_width': half_width,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_fly_1873(fly, output_path='Logs/jeans_fly_1873.svg',
                        debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in fly['points'].items()}
    curves = {k: v * s for k, v in fly['curves'].items()}
    con = {k: v * s for k, v in fly['construction'].items()}

    fig, ax = plt.subplots(1, 1, figsize=(6, 12))
    OUTLINE = dict(color='black', linewidth=1.5)

    # Fold line (dashed)
    ax.plot([pts['fold_bottom'][0], pts['fold_top'][0]],
            [pts['fold_bottom'][1], pts['fold_top'][1]],
            color='black', linewidth=1.5, linestyle='--')

    # Top edge
    ax.plot([pts['fold_top'][0], pts['outer_top'][0]],
            [pts['fold_top'][1], pts['outer_top'][1]], **OUTLINE)

    # Outer edge (straight portion)
    ax.plot([pts['outer_top'][0], pts['curve_start'][0]],
            [pts['outer_top'][1], pts['curve_start'][1]], **OUTLINE)

    # Bottom curve
    ax.plot(curves['bottom'][:, 0], curves['bottom'][:, 1], **OUTLINE)

    # Thin boundary line at the trim/inlay separation
    ax.plot([0, pts['outer_top'][0]],
            [con['inlay_y'], con['inlay_y']],
            color='dimgray', linewidth=0.8, linestyle='--')
    ax.annotate('trim here', (pts['outer_top'][0] / 2, con['inlay_y']),
                textcoords="offset points", xytext=(0, 5),
                fontsize=7, color='dimgray', ha='center')

    # Fold label
    mid_y = (pts['fold_bottom'][1] + pts['fold_top'][1]) / 2
    ax.annotate('FOLD', (pts['fold_bottom'][0] - 0.2 * s, mid_y),
                fontsize=8, ha='right', va='center', rotation=90)

    if debug:
        for name, pt in pts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6)

        _annotate_segment(ax, pts['fold_top'], pts['outer_top'], offset=(0, 8))
        _annotate_segment(ax, pts['fold_bottom'],
                          np.array([0, con['inlay_y']]), offset=(-14, 0))

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
    fly = draft_jeans_fly_1873(m, front)
    plot_jeans_fly_1873(fly, output_path, debug=debug, units=units)
