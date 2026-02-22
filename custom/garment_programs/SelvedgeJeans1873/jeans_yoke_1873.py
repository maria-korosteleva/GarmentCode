"""
Historical Jeans Yoke (1873 style)
Based on: Historical Tailoring Masterclasses - Drafting the Yoke

Drafted after the back panel is complete.  Separates the upper back panel
(waist to yoke line) from the lower back.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _annotate_segment, _draw_seam_allowance,
    _point_at_arclength, _curve_up_to_arclength,
)
from .jeans_back import draft_jeans_back


# -- Drafting ----------------------------------------------------------------

def draft_jeans_yoke(m, front, back, gathering_extension=0):
    """
    Compute yoke geometry from the completed front and back drafts.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of ``draft_jeans_front(m)``.
    back : dict
        Result of ``draft_jeans_back(m, front)``.
    gathering_extension : float, optional
        Extra length (in cm) to extend the yoke_seat point further along
        the seat_upper curve, creating gathering on the seat-seam side.
        Typical range: 0.5*INCH to 1*INCH.  Default 0 (no gathering).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fpts = front['points']
    bpts = back['points']

    # -- 1. Yoke point on outseam (side seam) --
    # 1.5" from pt 1 toward pt 4 along the back outseam (straight line)
    dir_1_to_4 = fpts['4'] - fpts['1']
    dir_1_to_4_norm = dir_1_to_4 / np.linalg.norm(dir_1_to_4)
    yoke_side = fpts['1'] + dir_1_to_4_norm * (1.5 * INCH)

    # -- 2. Yoke point on seat seam --
    # Walk the seat_upper curve (back_waist → 8') from the start by 2.75"
    yoke_seat_dist = 2.75 * INCH + gathering_extension
    yoke_seat = _point_at_arclength(back['curves']['seat_upper'], yoke_seat_dist)

    # -- 3. Dart position — 1/3 of waist from pt 1 toward back_waist --
    pt1 = fpts['1']
    back_waist = bpts['back_waist']
    waist_vec = back_waist - pt1
    waist_thirds_1 = pt1 + waist_vec / 3          # closest to pt 1
    waist_thirds_2 = pt1 + 2 * waist_vec / 3
    dart_center_waist = waist_thirds_1

    # -- 4. Dart guideline — perpendicular to waist, intersect yoke line --
    waist_dir_norm = waist_vec / np.linalg.norm(waist_vec)
    perp = np.array([-waist_dir_norm[1], waist_dir_norm[0]])
    # Ensure perpendicular points toward the yoke line (away from waist)
    yoke_mid = (yoke_side + yoke_seat) / 2
    if np.dot(perp, yoke_mid - dart_center_waist) < 0:
        perp = -perp

    # Line–line intersection:  dart_center_waist + t·perp = yoke_side + s·yoke_dir
    yoke_dir = yoke_seat - yoke_side
    A = np.column_stack([perp, -yoke_dir])
    b_vec = yoke_side - dart_center_waist
    params = np.linalg.solve(A, b_vec)
    dart_center_yoke = dart_center_waist + params[0] * perp

    # -- 5. Dart edges — 3/8" on each side along waist direction --
    hw = 3 / 8 * INCH
    dart_left_waist  = dart_center_waist - waist_dir_norm * hw
    dart_right_waist = dart_center_waist + waist_dir_norm * hw
    dart_left_yoke   = dart_center_yoke  - waist_dir_norm * hw
    dart_right_yoke  = dart_center_yoke  + waist_dir_norm * hw

    return {
        'points': {
            'yoke_side':          yoke_side,
            'yoke_seat':          yoke_seat,
            'dart_center_waist':  dart_center_waist,
            'dart_center_yoke':   dart_center_yoke,
            'dart_left_waist':    dart_left_waist,
            'dart_right_waist':   dart_right_waist,
            'dart_left_yoke':     dart_left_yoke,
            'dart_right_yoke':    dart_right_yoke,
        },
        'curves': {},          # all straight lines — no Bézier curves
        'construction': {
            'waist_thirds_1': waist_thirds_1,
            'waist_thirds_2': waist_thirds_2,
        },
        'metadata': {
            'title': 'Historical Jeans Yoke (1873)',
            'yoke_seat_dist': yoke_seat_dist,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_yoke(front, back, yoke, output_path='Logs/jeans_yoke.svg',
                    debug=False, units='cm'):
    """Render the yoke overlaid on the back panel and save as PNG.

    Always draws the yoke outline and dart.
    With debug=True, adds point labels, measurements, and grid.

    units : 'cm' or 'inch' — display unit for axes and annotations.
    """
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    fpts   = {k: v * s for k, v in front['points'].items()}
    bpts   = {k: v * s for k, v in back['points'].items()}
    bcurves = {k: v * s for k, v in back['curves'].items()}
    ypts   = {k: v * s for k, v in yoke['points'].items()}
    ycon   = {k: v * s for k, v in yoke['construction'].items()}

    # Seat-seam curve segment for yoke right side
    yoke_seat_dist = yoke['metadata']['yoke_seat_dist']
    seat_seg = _curve_up_to_arclength(back['curves']['seat_upper'], yoke_seat_dist) * s

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    OUTLINE  = dict(color='black', linewidth=1.5)
    CONTEXT  = dict(color='lightgray', linewidth=1, alpha=0.5)
    DART_STY = dict(color='black', linewidth=1.2, linestyle='--')

    # -- Back panel outline as context (light gray, debug only) --
    if debug:
        ax.plot([fpts['1'][0], bpts['back_waist'][0]],
                [fpts['1'][1], bpts['back_waist'][1]], **CONTEXT)
        ax.plot(bcurves['seat_upper'][:, 0], bcurves['seat_upper'][:, 1], **CONTEXT)
        ax.plot(bcurves['seat_lower'][:, 0], bcurves['seat_lower'][:, 1], **CONTEXT)
        ax.plot(bcurves['back_inseam'][:, 0], bcurves['back_inseam'][:, 1], **CONTEXT)
        ax.plot([bpts['12'][0], bpts['back_hem'][0]],
                [bpts['12'][1], bpts['back_hem'][1]], **CONTEXT)
        ax.plot([bpts['back_hem'][0], fpts['0'][0]],
                [bpts['back_hem'][1], fpts['0'][1]], **CONTEXT)
        ax.plot([fpts['0'][0], fpts['4'][0]],
                [fpts['0'][1], fpts['4'][1]], **CONTEXT)
        ax.plot([fpts['4'][0], fpts['1'][0]],
                [fpts['4'][1], fpts['1'][1]], **CONTEXT)

    # -- Yoke outline (black) --
    # Top: waist line (pt 1 → back_waist)
    ax.plot([fpts['1'][0], bpts['back_waist'][0]],
            [fpts['1'][1], bpts['back_waist'][1]], **OUTLINE)
    # Right side: seat_upper curve segment (back_waist → yoke_seat)
    ax.plot(seat_seg[:, 0], seat_seg[:, 1], **OUTLINE)
    # Bottom: yoke line (yoke_seat → yoke_side)
    ax.plot([ypts['yoke_seat'][0], ypts['yoke_side'][0]],
            [ypts['yoke_seat'][1], ypts['yoke_side'][1]], **OUTLINE)
    # Left side: outseam (yoke_side → pt 1) — straight line
    ax.plot([ypts['yoke_side'][0], fpts['1'][0]],
            [ypts['yoke_side'][1], fpts['1'][1]], **OUTLINE)

    # -- Notch on yoke seam (midpoint of straight yoke line) --
    _notch_mid = (ypts['yoke_seat'] + ypts['yoke_side']) / 2
    _seam_d    = ypts['yoke_seat'] - ypts['yoke_side']
    _seam_norm = _seam_d / np.linalg.norm(_seam_d)
    _perp      = np.array([-_seam_norm[1], _seam_norm[0]])
    _nsize     = 0.25 * INCH * s
    ax.plot([_notch_mid[0] - _perp[0]*_nsize, _notch_mid[0] + _perp[0]*_nsize],
            [_notch_mid[1] - _perp[1]*_nsize, _notch_mid[1] + _perp[1]*_nsize],
            color='black', linewidth=1.2)

    # -- Dart --
    ax.plot([ypts['dart_left_waist'][0],  ypts['dart_left_yoke'][0]],
            [ypts['dart_left_waist'][1],  ypts['dart_left_yoke'][1]],  **DART_STY)
    ax.plot([ypts['dart_right_waist'][0], ypts['dart_right_yoke'][0]],
            [ypts['dart_right_waist'][1], ypts['dart_right_yoke'][1]], **DART_STY)

    # -- Debug overlays --
    if debug:
        # Yoke point labels
        for name, pt in ypts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=7)

        # Construction: waist division points
        for label in ('waist_thirds_1', 'waist_thirds_2'):
            pt = ycon[label]
            ax.plot(pt[0], pt[1], 'x', color='blue', markersize=6, zorder=5)
            ax.annotate(label, pt, textcoords="offset points",
                        xytext=(6, -8), ha='left', fontsize=6, color='blue')

        # Dart center guideline
        ax.plot([ypts['dart_center_waist'][0], ypts['dart_center_yoke'][0]],
                [ypts['dart_center_waist'][1], ypts['dart_center_yoke'][1]],
                color='blue', linewidth=0.6, linestyle=':', alpha=0.5)

        # Measurements
        _annotate_segment(ax, fpts['1'], bpts['back_waist'], offset=(0, 8))
        _annotate_segment(ax, ypts['yoke_seat'], ypts['yoke_side'], offset=(0, -10))
        _annotate_segment(ax, ypts['dart_left_waist'], ypts['dart_right_waist'],
                          offset=(0, 8))

        # Back/front panel point labels (faint context)
        all_context = {**fpts, **bpts}
        for name, pt in all_context.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=3,
                    zorder=4, alpha=0.3)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6,
                        color='gray', alpha=0.4)

    # --- Seam allowances (always drawn) ---
    SA_SEAT_YOKE  = 5/8 * INCH   # long side / seat seam
    SA_SIDE_YOKE  = 3/4 * INCH   # short edge / side seam
    SA_WAIST_YOKE = 3/8 * INCH   # waist and yoke seams

    # CW outline: outseam(1→yoke_side) → yoke_line(yoke_side→yoke_seat)
    #   → seat_seg reversed(yoke_seat→back_waist) → waist(back_waist→1)
    sa_edges = [
        (np.array([fpts['1'], ypts['yoke_side']]),               SA_SIDE_YOKE),   # side seam
        (np.array([ypts['yoke_side'], ypts['yoke_seat']]),       SA_WAIST_YOKE),  # yoke seam (bottom)
        (seat_seg[::-1],                                         SA_SEAT_YOKE),   # seat seam segment (reversed)
        (np.array([bpts['back_waist'], fpts['1']]),              SA_WAIST_YOKE),  # waist
    ]
    _draw_seam_allowance(ax, sa_edges, scale=s)

    ax.set_title(yoke['metadata']['title'])
    ax.set_aspect('equal')
    ax.margins(0.05)
    if not debug:
        ax.axis('off')
    else:
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    back = draft_jeans_back(m, front)
    yoke = draft_jeans_yoke(m, front, back)
    plot_jeans_yoke(front, back, yoke, output_path, debug=debug, units=units)
