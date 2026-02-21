"""
Front Pocket (opening, bag, and facing)
Based on: Historical Tailoring Masterclasses - Drafting the Pockets and Accessories

Drafted on the front leg pattern:
1. Mark 3 1/4" from the outseam waist corner along the side seam
   → lower pocket opening point.
2. Mark 4 3/4" along the waist from the same corner
   → upper pocket opening point.
3. Connect with a smooth curve → pocket opening.
4. Add 3/8" SA to the opening.
5. Pocket bag: ~1" from opening, 10"–12" long, angled slightly upward
   toward the side seam, ending ~1 1/2" from the side seam.
6. Connect bag bottom to side seam ~2" below opening with a curve.
7. Pocket facing: ~1/2" inside the opening, depth 1"–2" below opening.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _curve_length, _annotate_segment,
    _point_at_arclength,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_front_pocket(m, front):
    """Draft the front pocket opening, bag, and facing.

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
    fpts = front['points']
    pt1 = fpts['1']

    # -- 1. Lower pocket opening: 3 1/4" along the outseam from pt1 --
    # The outseam runs: pt1 → 1' → hip curve → pt4.
    # Build a combined polyline and walk it by arc-length.
    outseam_path = np.vstack([pt1.reshape(1, 2), front['curves']['hip']])
    pocket_lower = _point_at_arclength(outseam_path, 3.25 * INCH)

    # -- 2. Upper pocket opening: 4 3/4" along the waist/rise from pt1 --
    # The waist/fly edge runs: pt1 → 1' → rise curve → 7'.
    rise_path = np.vstack([pt1.reshape(1, 2), front['curves']['rise']])
    pocket_upper = _point_at_arclength(rise_path, 4.75 * INCH)

    # -- 3. Pocket opening curve --
    chord = pocket_lower - pocket_upper
    chord_len = np.linalg.norm(chord)
    perp = np.array([chord[1], -chord[0]])
    perp_norm = perp / np.linalg.norm(perp)
    bow = chord_len * 0.15
    opening_curve = _bezier_cubic(
        pocket_upper,
        pocket_upper + (chord / 3) + perp_norm * bow,
        pocket_lower - (chord / 3) + perp_norm * bow,
        pocket_lower,
    )

    # -- 4. Pocket bag outline --
    bag_depth = 10.0 * INCH

    # bag_inner_top: 1" further along the rise from pocket_upper → ON the outline
    bag_inner_top = _point_at_arclength(rise_path, (4.75 + 1.0) * INCH)

    # Bag extends toward the hem, roughly parallel to the fly line
    fly_start = front['construction']['fly_start']
    fly_end = front['construction']['fly_end']
    fly_dir = fly_end - fly_start
    fly_dir_norm = fly_dir / np.linalg.norm(fly_dir)
    bag_inner_bottom = bag_inner_top + fly_dir_norm * bag_depth

    # Connection to side seam: ~2" below pocket opening along the outseam
    bag_sideseam = _point_at_arclength(outseam_path, (3.25 + 2.0) * INCH)

    # Bag bottom curve: from inner bottom, angling back to the side seam
    bag_bottom_curve = _bezier_cubic(
        bag_inner_bottom,
        bag_inner_bottom + np.array([0, bag_depth * 0.08]),
        bag_sideseam + fly_dir_norm * (1.5 * INCH),
        bag_sideseam,
    )

    return {
        'points': {
            'pocket_upper': pocket_upper,
            'pocket_lower': pocket_lower,
            'bag_inner_top': bag_inner_top,
            'bag_inner_bottom': bag_inner_bottom,
            'bag_sideseam': bag_sideseam,
        },
        'curves': {
            'opening': opening_curve,
            'bag_bottom': bag_bottom_curve,
        },
        'construction': {},
        'metadata': {
            'title': 'Front Pocket',
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_front_pocket(front, pocket, output_path='Logs/jeans_front_pocket.svg',
                            debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    fpts = {k: v * s for k, v in front['points'].items()}
    fcurves = {k: v * s for k, v in front['curves'].items()}
    ppts = {k: v * s for k, v in pocket['points'].items()}
    pcurves = {k: v * s for k, v in pocket['curves'].items()}

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    OUTLINE = dict(color='black', linewidth=1.5)
    POCKET = dict(color='darkorange', linewidth=1.5)
    BAG = dict(color='green', linewidth=1, linestyle='--')
    CONTEXT = dict(color='lightgray', linewidth=1, alpha=0.5)

    # -- Front panel context --
    if debug:
        for curve in fcurves.values():
            ax.plot(curve[:, 0], curve[:, 1], **CONTEXT)
        for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
            ax.plot([fpts[a][0], fpts[b][0]], [fpts[a][1], fpts[b][1]], **CONTEXT)
    else:
        # Show just the waist/side seam area for context
        ax.plot(fcurves['hip'][:, 0], fcurves['hip'][:, 1], **CONTEXT)
        ax.plot([fpts['4'][0], fpts['0'][0]],
                [fpts['4'][1], fpts['0'][1]], **CONTEXT)

    # -- Pocket opening curve --
    ax.plot(pcurves['opening'][:, 0], pcurves['opening'][:, 1], **POCKET)

    # -- Pocket bag --
    # Inner edge
    ax.plot([ppts['bag_inner_top'][0], ppts['bag_inner_bottom'][0]],
            [ppts['bag_inner_top'][1], ppts['bag_inner_bottom'][1]], **BAG)
    # Bottom curve
    ax.plot(pcurves['bag_bottom'][:, 0], pcurves['bag_bottom'][:, 1], **BAG)
    # Side edge back to pocket opening
    ax.plot([ppts['bag_sideseam'][0], ppts['pocket_lower'][0]],
            [ppts['bag_sideseam'][1], ppts['pocket_lower'][1]], **BAG)
    # Top edge (along opening)
    ax.plot([ppts['pocket_upper'][0], ppts['bag_inner_top'][0]],
            [ppts['pocket_upper'][1], ppts['bag_inner_top'][1]], **BAG)

    if debug:
        for name, pt in ppts.items():
            ax.plot(pt[0], pt[1], 'o', color='darkorange', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6)

        _annotate_segment(ax, ppts['pocket_upper'], ppts['pocket_lower'],
                          offset=(8, 0))

        # Front panel point labels (faint)
        for name, pt in fpts.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=3,
                    zorder=4, alpha=0.3)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6,
                        color='gray', alpha=0.4)

        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    ax.set_title(pocket['metadata']['title'])
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
    front = draft_jeans_front(m)
    pocket = draft_jeans_front_pocket(m, front)
    plot_jeans_front_pocket(front, pocket, output_path, debug=debug, units=units)
