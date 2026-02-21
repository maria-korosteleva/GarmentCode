"""
Historical Jeans Yoke – Modern (curved)
Based on: Historical Tailoring Masterclasses - Drafting the Yoke – Modern

Same anchor points as the 1873 yoke, but with TWO darts that are then
converted to curvature via slash-and-spread, producing smooth curved
waist and yoke lines.

Steps (from the lesson):
1. Same yoke depth marks: 1 1/2" on side seam, 2 3/4" from back_waist.
2. Yoke line connecting the two points.
3. Divide waist into 3 equal sections — TWO dart positions.
4. Square down from both waist points to the yoke line.
5. Smaller dart (at 1/3, nearer side seam): 1/4" wide (1/8" each side).
   Larger dart (at 2/3, nearer seat seam): 1/2" wide (1/4" each side).
6. Slash-and-spread: cut along one dart edge, overlap to leave 1/8"
   opening.  This converts the flat darts into curvature.
7. Blend top and bottom edges into smooth curves with a hip curve.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _annotate_segment, _annotate_curve,
    _point_at_arclength, _curve_up_to_arclength,
)
from .jeans_back import draft_jeans_back


# -- Helpers -----------------------------------------------------------------

def _rotate_point(pt, center, angle):
    """Rotate *pt* about *center* by *angle* (radians, CCW positive)."""
    c, s = np.cos(angle), np.sin(angle)
    R = np.array([[c, -s], [s, c]])
    return center + R @ (pt - center)


def _bezier_through_4(P0, Q1, Q2, P3, n=100):
    """Cubic Bezier that passes through P0, Q1, Q2, P3 at t = 0, 1/3, 2/3, 1.

    Solves for the control points CP1, CP2 analytically.
    """
    CP1 = (-5 * P0 + 18 * Q1 -  9 * Q2 + 2 * P3) / 6
    CP2 = ( 2 * P0 -  9 * Q1 + 18 * Q2 - 5 * P3) / 6
    return _bezier_cubic(P0, CP1, CP2, P3, n=n)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_yoke_modern(m, front, back):
    """
    Modern curved yoke via slash-and-spread of two darts.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of ``draft_jeans_front(m)``.
    back : dict
        Result of ``draft_jeans_back(m, front)``.

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fpts = front['points']
    bpts = back['points']

    # ------------------------------------------------------------------ #
    # 1-2. Same anchor points as 1873                                     #
    # ------------------------------------------------------------------ #
    # 1.5" from pt 1 toward pt 4 along the back outseam (straight line)
    dir_1_to_4 = fpts['4'] - fpts['1']
    dir_1_to_4_norm = dir_1_to_4 / np.linalg.norm(dir_1_to_4)
    yoke_side = fpts['1'] + dir_1_to_4_norm * (1.5 * INCH)
    yoke_seat = _point_at_arclength(back['curves']['seat_upper'], 2.75 * INCH)

    pt1 = fpts['1']
    back_waist = bpts['back_waist']

    # Waist line direction and perpendicular
    waist_vec = back_waist - pt1
    waist_len = np.linalg.norm(waist_vec)
    waist_dir = waist_vec / waist_len
    perp = np.array([-waist_dir[1], waist_dir[0]])
    yoke_mid = (yoke_side + yoke_seat) / 2
    if np.dot(perp, yoke_mid - pt1) < 0:
        perp = -perp

    # ------------------------------------------------------------------ #
    # 3-4. Two dart positions at 1/3 and 2/3 of waist                     #
    # ------------------------------------------------------------------ #
    dart1_waist = pt1 + waist_vec / 3        # closer to side seam (smaller)
    dart2_waist = pt1 + 2 * waist_vec / 3    # closer to seat seam (larger)

    # Dart tips: perpendicular from each waist point to the yoke line
    yoke_line_dir = yoke_seat - yoke_side

    def _yoke_intersect(waist_pt):
        A = np.column_stack([perp, -yoke_line_dir])
        b_vec = yoke_side - waist_pt
        params = np.linalg.solve(A, b_vec)
        return waist_pt + params[0] * perp, params[0]   # (point, dist)

    dart1_yoke, dart1_len = _yoke_intersect(dart1_waist)
    dart2_yoke, dart2_len = _yoke_intersect(dart2_waist)

    # ------------------------------------------------------------------ #
    # 5. Flat dart edges                                                   #
    # ------------------------------------------------------------------ #
    DART1_WIDTH = 1 / 4 * INCH    # smaller dart
    DART2_WIDTH = 1 / 2 * INCH    # larger dart
    REMAINING   = 1 / 8 * INCH    # opening left after manipulation

    d1_hw = DART1_WIDTH / 2
    d2_hw = DART2_WIDTH / 2

    # Edges on waist
    d1_left_w  = dart1_waist - waist_dir * d1_hw
    d1_right_w = dart1_waist + waist_dir * d1_hw
    d2_left_w  = dart2_waist - waist_dir * d2_hw
    d2_right_w = dart2_waist + waist_dir * d2_hw

    # Edges on yoke line
    d1_left_y  = dart1_yoke - waist_dir * d1_hw
    d1_right_y = dart1_yoke + waist_dir * d1_hw
    d2_left_y  = dart2_yoke - waist_dir * d2_hw
    d2_right_y = dart2_yoke + waist_dir * d2_hw

    # ------------------------------------------------------------------ #
    # 6. Slash-and-spread — compute rotation angles                        #
    # ------------------------------------------------------------------ #
    overlap1 = DART1_WIDTH - REMAINING     # 1/8"
    overlap2 = DART2_WIDTH - REMAINING     # 3/8"
    raw_angle1 = overlap1 / dart1_len
    raw_angle2 = overlap2 / dart2_len

    # Left section (outseam side) rotates about dart1_yoke.
    # Pick the sign that moves pt1 toward the center section.
    target1 = d1_right_w                   # center section's left boundary
    if (np.linalg.norm(_rotate_point(pt1, dart1_yoke,  raw_angle1) - target1) <
        np.linalg.norm(_rotate_point(pt1, dart1_yoke, -raw_angle1) - target1)):
        angle1 = raw_angle1
    else:
        angle1 = -raw_angle1

    # Right section (seat side) rotates about dart2_yoke.
    target2 = d2_left_w                    # center section's right boundary
    if (np.linalg.norm(_rotate_point(back_waist, dart2_yoke,  raw_angle2) - target2) <
        np.linalg.norm(_rotate_point(back_waist, dart2_yoke, -raw_angle2) - target2)):
        angle2 = raw_angle2
    else:
        angle2 = -raw_angle2

    # Rotated endpoints
    pt1_rot        = _rotate_point(pt1,        dart1_yoke, angle1)
    yoke_side_rot  = _rotate_point(yoke_side,  dart1_yoke, angle1)
    back_waist_rot = _rotate_point(back_waist, dart2_yoke, angle2)
    yoke_seat_rot  = _rotate_point(yoke_seat,  dart2_yoke, angle2)

    # ------------------------------------------------------------------ #
    # 7. Smooth curves through the manipulated points                      #
    # ------------------------------------------------------------------ #
    # Yoke curve (bottom): passes through
    #   yoke_side_rot → dart1_yoke → dart2_yoke → yoke_seat_rot
    yoke_curve = _bezier_through_4(
        yoke_side_rot, dart1_yoke, dart2_yoke, yoke_seat_rot)

    # Waist curve (top): passes through
    #   pt1_rot → dart1_waist → dart2_waist → back_waist_rot
    waist_curve = _bezier_through_4(
        pt1_rot, dart1_waist, dart2_waist, back_waist_rot)

    return {
        'points': {
            'yoke_side':       yoke_side,
            'yoke_seat':       yoke_seat,
            'yoke_side_rot':   yoke_side_rot,
            'yoke_seat_rot':   yoke_seat_rot,
            'pt1_rot':         pt1_rot,
            'back_waist_rot':  back_waist_rot,
            'dart1_waist':     dart1_waist,
            'dart2_waist':     dart2_waist,
            'dart1_yoke':      dart1_yoke,
            'dart2_yoke':      dart2_yoke,
        },
        'curves': {
            'yoke_line':  yoke_curve,
            'waist_line': waist_curve,
        },
        'construction': {
            'waist_thirds_1': dart1_waist,
            'waist_thirds_2': dart2_waist,
            # Flat dart edges (pre-manipulation)
            'd1_left_w':  d1_left_w,  'd1_right_w': d1_right_w,
            'd2_left_w':  d2_left_w,  'd2_right_w': d2_right_w,
            'd1_left_y':  d1_left_y,  'd1_right_y': d1_right_y,
            'd2_left_y':  d2_left_y,  'd2_right_y': d2_right_y,
        },
        'metadata': {
            'title': 'Historical Jeans Yoke \u2013 Modern (Curved)',
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_yoke_modern(front, back, yoke,
                           output_path='Logs/jeans_yoke_modern.svg',
                           debug=False, units='cm'):
    """Render the modern curved yoke overlaid on the back panel.

    Always draws the final smooth yoke outline.
    With debug=True, adds the flat dart construction, point labels, and grid.
    """
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    fpts    = {k: v * s for k, v in front['points'].items()}
    bpts    = {k: v * s for k, v in back['points'].items()}
    bcurves = {k: v * s for k, v in back['curves'].items()}
    ypts    = {k: v * s for k, v in yoke['points'].items()}
    ycurves = {k: v * s for k, v in yoke['curves'].items()}
    ycon    = {k: v * s for k, v in yoke['construction'].items()}

    # Seat-seam curve segment for yoke right side
    seat_seg = _curve_up_to_arclength(back['curves']['seat_upper'], 2.75 * INCH) * s

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    OUTLINE  = dict(color='black', linewidth=1.5)
    CONTEXT  = dict(color='lightgray', linewidth=1, alpha=0.5)
    FLAT_DART = dict(color='orange', linewidth=0.8, linestyle='--', alpha=0.6)

    # -- Back panel context (light gray, debug only) --
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

    # -- Yoke outline (black, smooth curves) --
    # Top: waist curve
    ax.plot(ycurves['waist_line'][:, 0], ycurves['waist_line'][:, 1], **OUTLINE)
    # Right side: seat seam segment (back_waist_rot → yoke_seat_rot)
    ax.plot([ypts['back_waist_rot'][0], ypts['yoke_seat_rot'][0]],
            [ypts['back_waist_rot'][1], ypts['yoke_seat_rot'][1]], **OUTLINE)
    # Bottom: yoke curve (reversed so we go right→left)
    ax.plot(ycurves['yoke_line'][::-1, 0], ycurves['yoke_line'][::-1, 1], **OUTLINE)
    # Left side: outseam segment (yoke_side_rot → pt1_rot)
    ax.plot([ypts['yoke_side_rot'][0], ypts['pt1_rot'][0]],
            [ypts['yoke_side_rot'][1], ypts['pt1_rot'][1]], **OUTLINE)

    # -- Debug overlays --
    if debug:
        # Flat dart construction (pre-manipulation)
        for prefix in ('d1', 'd2'):
            lw = ycon[f'{prefix}_left_w']
            rw = ycon[f'{prefix}_right_w']
            ly = ycon[f'{prefix}_left_y']
            ry = ycon[f'{prefix}_right_y']
            ax.plot([lw[0], ly[0]], [lw[1], ly[1]], **FLAT_DART)
            ax.plot([rw[0], ry[0]], [rw[1], ry[1]], **FLAT_DART)

        # Flat yoke line (pre-manipulation, straight)
        ax.plot([ypts['yoke_side'][0], ypts['yoke_seat'][0]],
                [ypts['yoke_side'][1], ypts['yoke_seat'][1]],
                color='orange', linewidth=0.6, linestyle=':', alpha=0.4)
        # Flat waist line
        ax.plot([fpts['1'][0], bpts['back_waist'][0]],
                [fpts['1'][1], bpts['back_waist'][1]],
                color='orange', linewidth=0.6, linestyle=':', alpha=0.4)

        # Point labels — yoke points
        for name, pt in ypts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6)

        # Construction division points
        for label in ('waist_thirds_1', 'waist_thirds_2'):
            pt = ycon[label]
            ax.plot(pt[0], pt[1], 'x', color='blue', markersize=6, zorder=5)
            ax.annotate(label, pt, textcoords="offset points",
                        xytext=(6, -8), ha='left', fontsize=6, color='blue')

        # Dart center guidelines
        for d_w, d_y in [(ypts['dart1_waist'], ypts['dart1_yoke']),
                         (ypts['dart2_waist'], ypts['dart2_yoke'])]:
            ax.plot([d_w[0], d_y[0]], [d_w[1], d_y[1]],
                    color='blue', linewidth=0.6, linestyle=':', alpha=0.5)

        # Measurements
        _annotate_curve(ax, ycurves['waist_line'], offset=(0, 8))
        _annotate_curve(ax, ycurves['yoke_line'], offset=(0, -10))

        # Back/front panel point labels (faint)
        for name, pt in {**fpts, **bpts}.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=3,
                    zorder=4, alpha=0.3)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6,
                        color='gray', alpha=0.4)

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
    yoke = draft_jeans_yoke_modern(m, front, back)
    plot_jeans_yoke_modern(front, back, yoke, output_path, debug=debug, units=units)
